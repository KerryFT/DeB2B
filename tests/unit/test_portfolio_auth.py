import base64

import pytest
from fastapi import HTTPException

from backend.infrastructure.config import Settings
from services.api.microsoft_auth import _allowed_email, _cookie_domain, _decode_state, _state_token


def settings() -> Settings:
    secret = base64.b64encode(b"s" * 32).decode()
    return Settings(
        app_env="portfolio",
        api_base_url="https://api.deb2b.id.vn",
        web_base_url="https://app.deb2b.id.vn",
        cors_allowed_origins="https://app.deb2b.id.vn",
        trusted_hosts="api.deb2b.id.vn",
        database_url="postgresql://app:placeholder@neon.example/ar",
        oidc_issuer="https://login.microsoftonline.com/common/v2.0",
        oidc_jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys",
        oidc_audience="client-id",
        dev_auth_enabled=False,
        metrics_bearer_token="metrics",  # noqa: S106
        microsoft_client_id="client-id",
        microsoft_client_secret="client-secret",  # noqa: S106
        microsoft_redirect_uri="https://api.deb2b.id.vn/api/v1/auth/microsoft/callback",
        portfolio_allowed_emails="Owner@Example.com",
        app_encryption_key=secret,
        session_secret=secret,
        document_upload_enabled=False,
        temporal_enabled=False,
        misa_api_enabled=False,
        outlook_webhook_enabled=False,
    )


def test_oauth_state_round_trip_and_cookie_domain() -> None:
    configured = settings()
    token = _state_token(configured, state="state", nonce="nonce", verifier="verifier")
    assert _decode_state(configured, token) == {
        "state": "state",
        "nonce": "nonce",
        "verifier": "verifier",
    }
    assert _cookie_domain(configured) == ".deb2b.id.vn"


def test_oauth_state_rejects_tampering() -> None:
    configured = settings()
    token = _state_token(configured, state="state", nonce="nonce", verifier="verifier")
    with pytest.raises(HTTPException):
        _decode_state(configured, token + "x")


def test_microsoft_account_is_restricted_to_allowlist() -> None:
    configured = settings()
    assert _allowed_email(configured, {"preferred_username": "owner@example.com"}) == (
        "owner@example.com"
    )
    with pytest.raises(HTTPException) as rejected:
        _allowed_email(configured, {"preferred_username": "attacker@example.com"})
    assert rejected.value.status_code == 403
