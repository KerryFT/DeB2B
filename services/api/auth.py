import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request
from jwt import PyJWKClient
from sqlalchemy import select

from backend.application.permissions import ROLE_PERMISSIONS, Permission, is_allowed
from backend.infrastructure.config import get_settings
from backend.infrastructure.database import SessionFactory, tenant_session
from backend.infrastructure.models import Membership, PortfolioSession, User


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    tenant_id: UUID
    role: str


async def current_actor(
    authorization: Annotated[str | None, Header()] = None,
    x_dev_user_id: Annotated[str | None, Header()] = None,
    x_dev_tenant_id: Annotated[str | None, Header()] = None,
    x_dev_role: Annotated[str, Header()] = "operator",
    request: Request = None,  # type: ignore[assignment]
) -> Actor:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name) if request else None
    if session_token:
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()
        with SessionFactory() as session:
            row = session.execute(
                select(PortfolioSession, Membership)
                .join(
                    Membership,
                    (Membership.user_id == PortfolioSession.user_id)
                    & (Membership.tenant_id == PortfolioSession.tenant_id),
                )
                .where(
                    PortfolioSession.token_hash == token_hash,
                    PortfolioSession.revoked_at.is_(None),
                    PortfolioSession.expires_at > datetime.now(UTC),
                )
            ).first()
        if row is None:
            raise HTTPException(401, "expired or revoked session")
        portfolio_session, membership = row
        return Actor(portfolio_session.user_id, portfolio_session.tenant_id, membership.role)
    if settings.dev_auth_enabled and x_dev_user_id and x_dev_tenant_id:
        if x_dev_role not in ROLE_PERMISSIONS:
            raise HTTPException(403, "invalid role")
        return Actor(UUID(x_dev_user_id), UUID(x_dev_tenant_id), x_dev_role)
    if not authorization:
        raise HTTPException(401, "missing bearer token")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "invalid authorization scheme")
    if not settings.oidc_jwks_uri:
        raise HTTPException(503, "OIDC JWKS is not configured")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = PyJWKClient(settings.oidc_jwks_uri).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "aud", "tenant_id"]},
        )
        tenant_id = UUID(claims["tenant_id"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(401, "invalid bearer token") from exc

    with tenant_session(tenant_id) as session:
        membership = session.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(
                User.issuer == claims["iss"],
                User.subject == claims["sub"],
                Membership.tenant_id == tenant_id,
            )
        ).first()
    if not membership:
        raise HTTPException(403, "user is not a member of this tenant")
    member, user = membership
    return Actor(user.id, tenant_id, member.role)


def validate_session_csrf(request: Request) -> None:
    settings = get_settings()
    session_token = request.cookies.get(settings.session_cookie_name)
    if not session_token:
        return
    supplied = request.headers.get("x-csrf-token")
    cookie_value = request.cookies.get("deb2b_csrf")
    if not supplied or not cookie_value or not hmac.compare_digest(supplied, cookie_value):
        raise HTTPException(403, "invalid CSRF token")
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    csrf_hash = hashlib.sha256(supplied.encode()).hexdigest()
    with SessionFactory() as session:
        exists = session.scalar(
            select(PortfolioSession.id).where(
                PortfolioSession.token_hash == token_hash,
                PortfolioSession.csrf_hash == csrf_hash,
                PortfolioSession.revoked_at.is_(None),
                PortfolioSession.expires_at > datetime.now(UTC),
            )
        )
    if exists is None:
        raise HTTPException(403, "invalid CSRF session")


def require_roles(*roles: str):  # type: ignore[no-untyped-def]
    async def dependency(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.role not in roles:
            raise HTTPException(403, "insufficient role")
        return actor

    return dependency


def require_permission(permission: Permission):  # type: ignore[no-untyped-def]
    async def dependency(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if not is_allowed(actor.role, permission):
            raise HTTPException(403, f"missing permission: {permission.value}")
        return actor

    return dependency
