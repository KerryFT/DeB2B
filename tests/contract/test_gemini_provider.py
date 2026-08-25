from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from backend.infrastructure.gemini_provider import GeminiLLMProvider


@pytest.mark.asyncio
async def test_gemini_provider_normalizes_structured_response_without_network() -> None:
    captured: dict[str, Any] = {}

    class Models:
        async def generate_content(self, **kwargs: Any) -> object:
            captured.update(kwargs)
            return SimpleNamespace(
                text='{"status":"ok"}',
                usage_metadata=SimpleNamespace(
                    prompt_token_count=12, candidates_token_count=4
                ),
            )

    provider = GeminiLLMProvider(api_key="fixture", timeout_seconds=5)
    provider.client = SimpleNamespace(aio=SimpleNamespace(models=Models()))  # type: ignore[assignment]
    result = await provider.generate_structured(
        task="fixture",
        prompt="safe fixture",
        schema={"type": "object", "properties": {"status": {"type": "string"}}},
        model="fixture-model",
    )

    assert result.schema_valid
    assert result.data == {"status": "ok"}
    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert captured["model"] == "fixture-model"
