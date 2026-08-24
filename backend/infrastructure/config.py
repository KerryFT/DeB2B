from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "AR Operations Agent"
    database_url: str = "postgresql+psycopg://ar:ar@localhost:55432/ar"
    temporal_target: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "ar-operations"
    oidc_issuer: str = "http://localhost:8000/dev-auth"
    oidc_audience: str = "ar-operations"
    oidc_jwks_uri: str | None = None
    dev_auth_enabled: bool = True
    llm_default_provider: str = "fake"
    automation_global_kill_switch: bool = True
    automation_external_delivery_enabled: bool = False
    upload_max_bytes: int = Field(default=26_214_400, gt=0)
    upload_max_pages: int = Field(default=100, gt=0)

    @model_validator(mode="after")
    def forbid_dev_auth_outside_development(self) -> "Settings":
        if self.app_env != "development" and self.dev_auth_enabled:
            raise ValueError("DEV_AUTH_ENABLED must be false outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
