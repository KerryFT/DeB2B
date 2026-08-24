from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.models import IdempotencyRecord


class IdempotencyConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StoredResponse:
    status_code: int
    body: dict[str, Any]


def request_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def find_stored_response(
    session: Session, *, tenant_id: UUID, key: str, payload: dict[str, Any]
) -> StoredResponse | None:
    record = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == tenant_id, IdempotencyRecord.key == key
        )
    )
    if record is None:
        return None
    if record.request_hash != request_fingerprint(payload):
        raise IdempotencyConflict("idempotency key was already used with a different request")
    return StoredResponse(record.response_code, record.response_body)


def store_response(
    session: Session,
    *,
    tenant_id: UUID,
    key: str,
    request: dict[str, Any],
    response: StoredResponse,
) -> None:
    session.add(
        IdempotencyRecord(
            tenant_id=tenant_id,
            key=key,
            request_hash=request_fingerprint(request),
            response_code=response.status_code,
            response_body=response.body,
        )
    )
