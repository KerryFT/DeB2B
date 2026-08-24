from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LLMResult:
    provider: str
    model: str
    data: dict[str, Any] | None
    text: str | None
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    request_id: str | None = None
    schema_valid: bool = False
    error_class: str | None = None


class LLMProvider(Protocol):
    name: str

    async def generate_structured(
        self, *, task: str, prompt: str, schema: dict[str, Any], model: str
    ) -> LLMResult: ...

    async def generate_text(self, *, task: str, prompt: str, model: str) -> LLMResult: ...


class ObjectStorage(Protocol):
    async def put(self, *, tenant_id: str, key: str, content: bytes, content_type: str) -> str: ...

    async def get(self, *, tenant_id: str, key: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class DraftSpec:
    to: tuple[str, ...]
    cc: tuple[str, ...]
    subject: str
    body: str
    attachment_keys: tuple[str, ...] = ()


class GmailPort(Protocol):
    async def create_draft(self, *, idempotency_key: str, spec: DraftSpec) -> str: ...
