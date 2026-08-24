from __future__ import annotations

import time
from typing import Any, Protocol

from backend.application.ports import LLMResult


class StructuredTransport(Protocol):
    async def __call__(
        self, *, provider: str, model: str, prompt: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


def compile_portable_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Restrict JSON Schema to the shared provider subset."""
    allowed = {
        "$defs",
        "$ref",
        "additionalProperties",
        "anyOf",
        "description",
        "enum",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "properties",
        "required",
        "title",
        "type",
    }

    def clean(value: Any, *, named_schema_map: bool = False) -> Any:
        if isinstance(value, dict):
            if named_schema_map:
                return {key: clean(item) for key, item in value.items()}
            return {
                key: clean(item, named_schema_map=key in {"$defs", "properties"})
                for key, item in value.items()
                if key in allowed
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    compiled = clean(schema)
    if not isinstance(compiled, dict) or compiled.get("type") != "object":
        raise ValueError("portable structured output requires an object root")
    compiled["additionalProperties"] = False
    return compiled


class TransportLLMAdapter:
    name = "base"

    def __init__(self, transport: StructuredTransport) -> None:
        self.transport = transport

    async def generate_structured(
        self, *, task: str, prompt: str, schema: dict[str, Any], model: str
    ) -> LLMResult:
        del task
        started = time.perf_counter()
        try:
            data = await self.transport(
                provider=self.name,
                model=model,
                prompt=prompt,
                schema=compile_portable_schema(schema),
            )
            return LLMResult(
                self.name,
                model,
                data,
                None,
                round((time.perf_counter() - started) * 1000),
                schema_valid=True,
            )
        except Exception as exc:
            return LLMResult(
                self.name,
                model,
                None,
                None,
                round((time.perf_counter() - started) * 1000),
                error_class=type(exc).__name__,
            )

    async def generate_text(self, *, task: str, prompt: str, model: str) -> LLMResult:
        del task
        result = await self.generate_structured(
            task="text", prompt=prompt, schema={"type": "object", "properties": {}}, model=model
        )
        return result


class OpenAIAdapter(TransportLLMAdapter):
    name = "openai"


class GeminiAdapter(TransportLLMAdapter):
    name = "gemini"


class AnthropicAdapter(TransportLLMAdapter):
    name = "anthropic"
