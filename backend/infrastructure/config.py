import base64
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "portfolio", "staging", "production"] = (
        "development"
    )
    app_name: str = "AR Operations Agent"
    api_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    cors_allowed_origins: str = ""
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    database_url: str = "postgresql+psycopg://ar:ar@localhost:55432/ar"
    temporal_target: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "ar-operations"
    oidc_issuer: str = "http://localhost:8000/dev-auth"
    oidc_audience: str = "ar-operations"
    oidc_jwks_uri: str | None = None
    dev_auth_enabled: bool = True
    s3_endpoint: str | None = "http://localhost:9000"
    s3_bucket: str = "ar-documents"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    s3_server_side_encryption: Literal["AES256", "aws:kms"] | None = None
    clamav_host: str | None = "localhost"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    metrics_bearer_token: str | None = None
    llm_default_provider: Literal["fake", "gemini", "openai", "anthropic"] = "fake"
    gemini_api_key: str | None = None
    gemini_model_fast: str = "gemini-3.5-flash-lite"
    gemini_model_reasoning: str = "gemini-3.7-flash"
    llm_timeout_seconds: float = Field(default=20, ge=5, le=120)
    automation_global_kill_switch: bool = True
    automation_external_delivery_enabled: bool = False
    document_upload_enabled: bool = True
    temporal_enabled: bool = True
    misa_api_enabled: bool = False
    misa_import_enabled: bool = True
    outlook_sync_enabled: bool = False
    outlook_webhook_enabled: bool = False
    outlook_draft_enabled: bool = False
    outlook_send_enabled: bool = False
    microsoft_tenant: str = "common"
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_redirect_uri: str | None = None
    portfolio_allowed_emails: str = ""
    portfolio_tenant_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    app_encryption_key: str | None = None
    session_secret: str | None = None
    session_cookie_name: str = "deb2b_session"
    session_cookie_domain: str | None = None
    session_ttl_minutes: int = Field(default=60, ge=15, le=480)
    upload_max_bytes: int = Field(default=26_214_400, gt=0)
    upload_max_pages: int = Field(default=100, gt=0)

    @field_validator("database_url", mode="before")
    @classmethod
    def select_psycopg_driver(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator(
        "oidc_jwks_uri",
        "s3_endpoint",
        "s3_access_key",
        "s3_secret_key",
        "s3_server_side_encryption",
        "clamav_host",
        "metrics_bearer_token",
        "gemini_api_key",
        "microsoft_client_id",
        "microsoft_client_secret",
        "microsoft_redirect_uri",
        "app_encryption_key",
        "session_secret",
        "session_cookie_domain",
        mode="before",
    )
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def cors_origins(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.cors_allowed_origins.split(",") if part.strip())

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.trusted_hosts.split(",") if part.strip())

    @property
    def allowed_portfolio_emails(self) -> frozenset[str]:
        return frozenset(
            part.strip().casefold()
            for part in self.portfolio_allowed_emails.split(",")
            if part.strip()
        )

    @staticmethod
    def _decode_32_byte_secret(name: str, value: str | None) -> bytes:
        if not value:
            raise ValueError(f"{name} is required")
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise ValueError(f"{name} must be valid base64") from exc
        if len(decoded) != 32:
            raise ValueError(f"{name} must encode exactly 32 bytes")
        return decoded

    @property
    def encryption_key_bytes(self) -> bytes:
        return self._decode_32_byte_secret("APP_ENCRYPTION_KEY", self.app_encryption_key)

    @property
    def session_secret_bytes(self) -> bytes:
        return self._decode_32_byte_secret("SESSION_SECRET", self.session_secret)

    @model_validator(mode="after")
    def enforce_environment_safety(self) -> "Settings":
        if self.app_env != "development" and self.dev_auth_enabled:
            raise ValueError("DEV_AUTH_ENABLED must be false outside development")
        if self.app_env in {"portfolio", "staging", "production"}:
            common_required = {
                "OIDC_JWKS_URI": self.oidc_jwks_uri,
                "METRICS_BEARER_TOKEN": self.metrics_bearer_token,
            }
            common_missing = sorted(name for name, value in common_required.items() if not value)
            if common_missing:
                raise ValueError(
                    f"missing required {self.app_env} settings: {', '.join(common_missing)}"
                )
            urls = {
                "API_BASE_URL": self.api_base_url,
                "WEB_BASE_URL": self.web_base_url,
                "OIDC_ISSUER": self.oidc_issuer,
                "OIDC_JWKS_URI": self.oidc_jwks_uri or "",
            }
            insecure = [name for name, value in urls.items() if urlparse(value).scheme != "https"]
            if insecure:
                raise ValueError(f"HTTPS is required for: {', '.join(insecure)}")
            database = urlparse(self.database_url.replace("postgresql+psycopg", "postgresql"))
            if database.scheme != "postgresql" or database.hostname in {
                None,
                "localhost",
                "127.0.0.1",
            }:
                raise ValueError("deployed database must be a non-local PostgreSQL service")
            if not self.cors_origins:
                raise ValueError("CORS_ALLOWED_ORIGINS must contain the exact deployed web origin")
            if self.automation_external_delivery_enabled or not self.automation_global_kill_switch:
                raise ValueError(
                    "initial deployed release requires external delivery off and global kill on"
                )
            if self.llm_default_provider == "gemini" and not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is required when LLM_DEFAULT_PROVIDER=gemini")

        if self.app_env == "portfolio":
            portfolio_required = {
                "MICROSOFT_CLIENT_ID": self.microsoft_client_id,
                "MICROSOFT_CLIENT_SECRET": self.microsoft_client_secret,
                "MICROSOFT_REDIRECT_URI": self.microsoft_redirect_uri,
                "PORTFOLIO_ALLOWED_EMAILS": self.portfolio_allowed_emails,
                "APP_ENCRYPTION_KEY": self.app_encryption_key,
                "SESSION_SECRET": self.session_secret,
            }
            portfolio_missing = sorted(
                name for name, value in portfolio_required.items() if not value
            )
            if portfolio_missing:
                raise ValueError(
                    "missing required portfolio settings: " + ", ".join(portfolio_missing)
                )
            self._decode_32_byte_secret("APP_ENCRYPTION_KEY", self.app_encryption_key)
            self._decode_32_byte_secret("SESSION_SECRET", self.session_secret)
            if (
                not self.microsoft_redirect_uri
                or urlparse(self.microsoft_redirect_uri).scheme != "https"
            ):
                raise ValueError("MICROSOFT_REDIRECT_URI must use HTTPS in portfolio")
            if self.outlook_send_enabled:
                raise ValueError("OUTLOOK_SEND_ENABLED must remain false in portfolio")
            unsafe_portfolio_features = {
                "DOCUMENT_UPLOAD_ENABLED": self.document_upload_enabled,
                "TEMPORAL_ENABLED": self.temporal_enabled,
                "MISA_API_ENABLED": self.misa_api_enabled,
                "OUTLOOK_WEBHOOK_ENABLED": self.outlook_webhook_enabled,
            }
            enabled = sorted(name for name, value in unsafe_portfolio_features.items() if value)
            if enabled:
                raise ValueError(
                    "portfolio release requires unsupported features off: " + ", ".join(enabled)
                )

        if self.app_env in {"staging", "production"}:
            required = {
                "S3_ENDPOINT": self.s3_endpoint,
                "S3_ACCESS_KEY": self.s3_access_key,
                "S3_SECRET_KEY": self.s3_secret_key,
                "CLAMAV_HOST": self.clamav_host,
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise ValueError(f"missing required {self.app_env} settings: {', '.join(missing)}")
            if self.llm_default_provider == "fake":
                raise ValueError("LLM_DEFAULT_PROVIDER=fake is forbidden outside local/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
