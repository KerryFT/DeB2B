import pytest
from pydantic import ValidationError

from backend.infrastructure.config import Settings


def test_dev_auth_forbidden_outside_development() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", dev_auth_enabled=True)
