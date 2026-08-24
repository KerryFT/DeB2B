import pytest

from backend.infrastructure.llm_adapters import (
    AnthropicAdapter,
    GeminiAdapter,
    OpenAIAdapter,
    compile_portable_schema,
)


def test_portable_schema_removes_provider_specific_keywords() -> None:
    result = compile_portable_schema(
        {
            "type": "object",
            "properties": {"invoice": {"type": "string", "pattern": "INV-.*"}},
            "required": ["invoice"],
            "unevaluatedProperties": False,
        }
    )
    assert result["additionalProperties"] is False
    assert "pattern" not in result["properties"]["invoice"]


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_type", [OpenAIAdapter, GeminiAdapter, AnthropicAdapter])
async def test_all_provider_adapters_share_offline_contract(adapter_type) -> None:
    calls = []

    async def transport(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs)
        return {"invoice_number": "INV-1"}

    adapter = adapter_type(transport)
    result = await adapter.generate_structured(
        task="invoice",
        prompt="fixture",
        schema={"type": "object", "properties": {"invoice_number": {"type": "string"}}},
        model="fixture-model",
    )
    assert result.provider == adapter.name
    assert result.schema_valid
    assert result.data == {"invoice_number": "INV-1"}
    assert calls[0]["schema"]["additionalProperties"] is False
