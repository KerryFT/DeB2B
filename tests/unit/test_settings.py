import base64

import pytest
from pydantic import ValidationError

from backend.infrastructure.config import Settings

TEST_SECRET = base64.b64encode(b"x" * 32).decode()


def test_dev_auth_forbidden_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", dev_auth_enabled=True)


def test_empty_optional_environment_values_are_none() -> None:
    settings = Settings(s3_server_side_encryption="")  # type: ignore[arg-type]
    assert settings.s3_server_side_encryption is None


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "api_base_url": "https://api.deb2b.id.vn",
        "web_base_url": "https://deb2b.id.vn",
        "cors_allowed_origins": "https://deb2b.id.vn",
        "database_url": "postgresql://app:placeholder@postgres.internal/ar",
        "oidc_issuer": "https://identity.example.test/",
        "oidc_jwks_uri": "https://identity.example.test/.well-known/jwks.json",
        "dev_auth_enabled": False,
        "s3_endpoint": "https://objects.example.test",
        "s3_access_key": "placeholder-access",
        "s3_secret_key": "placeholder-secret",  # noqa: S106 - synthetic test value
        "clamav_host": "clamav.internal",
        "metrics_bearer_token": "placeholder-metrics",  # noqa: S106
        "llm_default_provider": "openai",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_settings_are_strict_and_normalize_railway_postgres_url() -> None:
    settings = production_settings()
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.cors_origins == ("https://deb2b.id.vn",)


def test_portfolio_profile_allows_fake_llm_but_disables_unsupported_runtime_services() -> None:
    settings = Settings(**portfolio_values())  # type: ignore[arg-type]
    assert settings.app_env == "portfolio"
    assert settings.misa_import_enabled
    assert settings.outlook_sync_enabled


@pytest.mark.parametrize(
    "feature",
    [
        "document_upload_enabled",
        "temporal_enabled",
        "misa_api_enabled",
        "outlook_webhook_enabled",
    ],
)
def test_portfolio_profile_fails_if_unsupported_feature_is_enabled(feature: str) -> None:
    values = portfolio_values()
    values[feature] = True
    with pytest.raises(ValidationError):
        Settings(**values)  # type: ignore[arg-type]


def portfolio_values() -> dict[str, object]:
    return {
        "app_env": "portfolio",
        "api_base_url": "https://api.deb2b.id.vn",
        "web_base_url": "https://app.deb2b.id.vn",
        "cors_allowed_origins": "https://app.deb2b.id.vn",
        "trusted_hosts": "api.deb2b.id.vn",
        "database_url": "postgresql://app:placeholder@neon.example/ar",
        "oidc_issuer": "https://login.microsoftonline.com/common/v2.0",
        "oidc_jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
        "oidc_audience": "placeholder-client-id",
        "dev_auth_enabled": False,
        "metrics_bearer_token": "placeholder-metrics",
        "microsoft_client_id": "placeholder-client-id",
        "microsoft_client_secret": "placeholder-client-secret",
        "microsoft_redirect_uri": "https://api.deb2b.id.vn/api/v1/auth/microsoft/callback",
        "portfolio_allowed_emails": "owner@example.com",
        "app_encryption_key": TEST_SECRET,
        "session_secret": TEST_SECRET,
        "document_upload_enabled": False,
        "temporal_enabled": False,
        "misa_api_enabled": False,
        "misa_import_enabled": True,
        "outlook_sync_enabled": True,
        "outlook_webhook_enabled": False,
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("database_url", "postgresql://ar:ar@localhost/ar"),
        ("oidc_jwks_uri", None),
        ("llm_default_provider", "fake"),
        ("automation_global_kill_switch", False),
        ("automation_external_delivery_enabled", True),
    ],
)
def test_unsafe_production_settings_fail_fast(key: str, value: object) -> None:
    with pytest.raises(ValidationError):
        production_settings(**{key: value})
