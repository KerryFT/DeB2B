import pytest

from backend.application.ports import DraftSpec
from backend.infrastructure.fakes import FakeGmail, FakeLLMProvider, MemoryObjectStorage


@pytest.mark.asyncio
async def test_fake_llm_obeys_normalized_contract() -> None:
    provider = FakeLLMProvider({"classify": {"type": "invoice"}})
    result = await provider.generate_structured(
        task="classify", prompt="untrusted input", schema={"type": "object"}, model="fake-v1"
    )
    assert result.provider == "fake"
    assert result.schema_valid
    assert result.data == {"type": "invoice"}


@pytest.mark.asyncio
async def test_fake_gmail_draft_is_idempotent() -> None:
    gmail = FakeGmail()
    spec = DraftSpec(("ap@example.com",), (), "Subject", "Body")
    first = await gmail.create_draft(idempotency_key="tenant:case:draft", spec=spec)
    second = await gmail.create_draft(idempotency_key="tenant:case:draft", spec=spec)
    assert first == second
    assert len(gmail.drafts) == 1


@pytest.mark.asyncio
async def test_memory_storage_is_tenant_namespaced() -> None:
    storage = MemoryObjectStorage()
    key = await storage.put(tenant_id="t1", key="hash", content=b"one", content_type="text/plain")
    assert key == "t1/hash"
    assert await storage.get(tenant_id="t1", key="hash") == b"one"
