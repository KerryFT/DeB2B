from __future__ import annotations

from functools import lru_cache

from backend.application.ports import LLMProvider
from backend.infrastructure.config import get_settings
from backend.infrastructure.fakes import FakeLLMProvider
from backend.infrastructure.gemini_provider import GeminiLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_default_provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini is selected but GEMINI_API_KEY is missing")
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return FakeLLMProvider()


def reset_llm_provider() -> None:
    get_llm_provider.cache_clear()
