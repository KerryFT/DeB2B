from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from jwt import PyJWKClient
from sqlalchemy import select

from backend.infrastructure.config import Settings, get_settings
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.gmail_oauth import CredentialCipher
from backend.infrastructure.models import (
    ConnectorConfig,
    ConnectorCredential,
    Membership,
    PortfolioSession,
    Tenant,
    User,
)

router = APIRouter(prefix="/api/v1/auth/microsoft", tags=["authentication"])

OAUTH_SCOPES = ("openid", "profile", "email", "offline_access", "User.Read", "Mail.ReadWrite")
STATE_COOKIE = "deb2b_oauth_state"
CSRF_COOKIE = "deb2b_csrf"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _cookie_domain(settings: Settings) -> str | None:
    if settings.session_cookie_domain:
        return settings.session_cookie_domain
    host = urlparse(settings.web_base_url).hostname or ""
    if host == "deb2b.id.vn" or host.endswith(".deb2b.id.vn"):
        return ".deb2b.id.vn"
    return None


def _state_token(settings: Settings, *, state: str, nonce: str, verifier: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "state": state,
            "nonce": nonce,
            "verifier": verifier,
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "aud": "deb2b-oauth-state",
        },
        settings.session_secret_bytes,
        algorithm="HS256",
    )


def _decode_state(settings: Settings, token: str) -> dict[str, str]:
    try:
        claims = jwt.decode(
            token,
            settings.session_secret_bytes,
            algorithms=["HS256"],
            audience="deb2b-oauth-state",
            options={"require": ["state", "nonce", "verifier", "iat", "exp", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(400, "invalid or expired OAuth state") from exc
    return {key: str(claims[key]) for key in ("state", "nonce", "verifier")}


@router.get("/login")
async def microsoft_login() -> Response:
    settings = get_settings()
    if not settings.microsoft_client_id or not settings.microsoft_redirect_uri:
        raise HTTPException(503, "Microsoft authentication is not configured")
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=")
    query = urlencode(
        {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(OAUTH_SCOPES),
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge.decode(),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(
        f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/authorize?{query}"
    )
    response.set_cookie(
        STATE_COOKIE,
        _state_token(settings, state=state, nonce=nonce, verifier=verifier),
        max_age=600,
        httponly=True,
        secure=settings.app_env != "development",
        samesite="lax",
        path="/api/v1/auth/microsoft",
    )
    return response


def _validate_id_token(settings: Settings, token: str, *, expected_nonce: str) -> dict[str, object]:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        tenant_id = str(unverified["tid"])
        issuer = str(unverified["iss"])
        expected_issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        if issuer != expected_issuer:
            raise jwt.InvalidIssuerError("issuer does not match token tenant")
        signing_key = PyJWKClient(
            "https://login.microsoftonline.com/common/discovery/v2.0/keys"
        ).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.microsoft_client_id,
            issuer=expected_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "aud", "nonce", "tid"]},
        )
        if not secrets.compare_digest(str(claims["nonce"]), expected_nonce):
            raise jwt.InvalidTokenError("nonce mismatch")
        return claims
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, "Microsoft identity token validation failed") from exc


def _allowed_email(settings: Settings, claims: dict[str, object]) -> str:
    email = str(
        claims.get("email") or claims.get("preferred_username") or claims.get("upn") or ""
    ).strip()
    if not email or email.casefold() not in settings.allowed_portfolio_emails:
        raise HTTPException(403, "this Microsoft account is not allowed")
    return email


@router.get("/callback")
async def microsoft_callback(request: Request, code: str = "", state: str = "") -> Response:
    settings = get_settings()
    state_cookie = request.cookies.get(STATE_COOKIE)
    if not code or not state or not state_cookie:
        raise HTTPException(400, "incomplete OAuth callback")
    stored = _decode_state(settings, state_cookie)
    if not secrets.compare_digest(stored["state"], state):
        raise HTTPException(400, "OAuth state mismatch")
    if not all(
        (
            settings.microsoft_client_id,
            settings.microsoft_client_secret,
            settings.microsoft_redirect_uri,
        )
    ):
        raise HTTPException(503, "Microsoft authentication is not configured")
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/token",
            data={
                "client_id": settings.microsoft_client_id,
                "client_secret": settings.microsoft_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.microsoft_redirect_uri,
                "code_verifier": stored["verifier"],
                "scope": " ".join(OAUTH_SCOPES),
            },
            timeout=30,
        )
    if token_response.status_code != 200:
        raise HTTPException(401, "Microsoft token exchange failed")
    token_payload = token_response.json()
    granted_scopes = {item.casefold() for item in str(token_payload.get("scope", "")).split()}
    if "mail.readwrite" not in granted_scopes:
        raise HTTPException(403, "Microsoft consent did not grant Mail.ReadWrite")
    claims = _validate_id_token(
        settings, str(token_payload.get("id_token", "")), expected_nonce=stored["nonce"]
    )
    email = _allowed_email(settings, claims)
    issuer = str(claims["iss"])
    subject = str(claims["sub"])
    expires_at = datetime.now(UTC) + timedelta(seconds=int(token_payload.get("expires_in", 3600)))
    cipher = CredentialCipher(settings.encryption_key_bytes)
    ciphertext = cipher.encrypt(token_payload, tenant_id=str(settings.portfolio_tenant_id))
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    session_expires = datetime.now(UTC) + timedelta(minutes=settings.session_ttl_minutes)
    with SessionFactory.begin() as database:
        tenant = database.get(Tenant, settings.portfolio_tenant_id)
        if tenant is None:
            tenant = Tenant(id=settings.portfolio_tenant_id, name="DeB2B Portfolio")
            database.add(tenant)
            database.flush()
        user = database.scalar(select(User).where(User.issuer == issuer, User.subject == subject))
        if user is None:
            user = User(issuer=issuer, subject=subject, email=email)
            database.add(user)
            database.flush()
        else:
            user.email = email
        membership = database.scalar(
            select(Membership).where(
                Membership.tenant_id == settings.portfolio_tenant_id,
                Membership.user_id == user.id,
            )
        )
        if membership is None:
            database.add(
                Membership(tenant_id=settings.portfolio_tenant_id, user_id=user.id, role="admin")
            )
        credential = database.scalar(
            select(ConnectorCredential).where(
                ConnectorCredential.tenant_id == settings.portfolio_tenant_id,
                ConnectorCredential.provider == "outlook",
                ConnectorCredential.account == email,
            )
        )
        if credential is None:
            credential = ConnectorCredential(
                tenant_id=settings.portfolio_tenant_id,
                provider="outlook",
                account=email,
                ciphertext=ciphertext,
                scopes=str(token_payload.get("scope", "")).split(),
                expires_at=expires_at,
                status="CONNECTED",
            )
            database.add(credential)
        else:
            credential.ciphertext = ciphertext
            credential.scopes = str(token_payload.get("scope", "")).split()
            credential.expires_at = expires_at
            credential.status = "CONNECTED"
        connector = database.scalar(
            select(ConnectorConfig).where(
                ConnectorConfig.tenant_id == settings.portfolio_tenant_id,
                ConnectorConfig.provider == "outlook",
            )
        )
        if connector is None:
            connector = ConnectorConfig(
                tenant_id=settings.portfolio_tenant_id,
                provider="outlook",
                environment="portfolio",
                secret_reference="database://connector_credentials/outlook",  # noqa: S106
                capabilities=["email.read", "draft.create"],
                settings={"mode": "manual-delta", "webhook": False, "send": False},
                enabled=True,
            )
            database.add(connector)
        else:
            connector.environment = "portfolio"
            connector.secret_reference = "database://connector_credentials/outlook"  # noqa: S105
            connector.capabilities = ["email.read", "draft.create"]
            connector.settings = {"mode": "manual-delta", "webhook": False, "send": False}
            connector.enabled = True
        database.add(
            PortfolioSession(
                token_hash=_hash(session_token),
                csrf_hash=_hash(csrf_token),
                tenant_id=settings.portfolio_tenant_id,
                user_id=user.id,
                expires_at=session_expires,
            )
        )
    response = RedirectResponse(f"{settings.web_base_url}/settings?outlook=connected")
    response.delete_cookie(STATE_COOKIE, path="/api/v1/auth/microsoft")
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=False,
        secure=True,
        samesite="lax",
        domain=_cookie_domain(settings),
        path="/",
    )
    return response


@router.post("/logout")
async def microsoft_logout(request: Request) -> Response:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        with SessionFactory.begin() as database:
            record = database.scalar(
                select(PortfolioSession).where(PortfolioSession.token_hash == _hash(session_token))
            )
            if record is not None:
                record.revoked_at = datetime.now(UTC)
    response = Response(status_code=204)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(CSRF_COOKIE, domain=_cookie_domain(settings), path="/")
    return response
