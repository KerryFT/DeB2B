from __future__ import annotations

import json
from typing import Any

from backend.application.ports import DraftSpec, LLMResult


class FakeLLMProvider:
    name = "fake"

    def __init__(self, fixtures: dict[str, dict[str, Any]] | None = None) -> None:
        self.fixtures = fixtures or {}

    async def generate_structured(
        self, *, task: str, prompt: str, schema: dict[str, Any], model: str
    ) -> LLMResult:
        data = self.fixtures.get(task, {})
        return LLMResult(self.name, model, data, None, 0, schema_valid=True)

    async def generate_text(self, *, task: str, prompt: str, model: str) -> LLMResult:
        text = str(self.fixtures.get(task, {}).get("text", "Synthetic draft for review."))
        return LLMResult(self.name, model, None, text, 0, schema_valid=True)


class FakeGmail:
    def __init__(self) -> None:
        self.drafts: dict[str, tuple[str, DraftSpec]] = {}

    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str:
        if idempotency_key in self.drafts:
            return self.drafts[idempotency_key][0]
        draft_id = f"fake-draft-{len(self.drafts) + 1}"
        self.drafts[idempotency_key] = (draft_id, spec)
        return draft_id


class MemoryObjectStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, *, tenant_id: str, key: str, content: bytes, content_type: str) -> str:
        object_key = f"{tenant_id}/{key}"
        self.objects.setdefault(object_key, content)
        return object_key

    async def get(self, *, tenant_id: str, key: str) -> bytes:
        return self.objects[f"{tenant_id}/{key}"]

    def snapshot(self) -> str:
        return json.dumps(sorted(self.objects), separators=(",", ":"))


class FakeMalwareScanner:
    def __init__(self, *, clean: bool = True) -> None:
        self.clean = clean
        self.calls = 0

    async def is_clean(self, content: bytes) -> bool:
        self.calls += 1
        return self.clean
