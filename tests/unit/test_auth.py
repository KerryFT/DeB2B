import pytest
from fastapi import HTTPException

from backend.infrastructure.config import get_settings
from services.api.auth import current_actor


@pytest.mark.asyncio
async def test_missing_or_malformed_auth_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH_ENABLED", "false")
    monkeypatch.setenv("OIDC_JWKS_URI", "https://issuer.invalid/jwks")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as missing:
        await current_actor(None, None, None, "operator")
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as malformed:
        await current_actor("Basic abc", None, None, "operator")
    assert malformed.value.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_dev_auth_rejects_forged_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as denied:
        await current_actor(
            None,
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            "owner",
        )
    assert denied.value.status_code == 403
    get_settings.cache_clear()
