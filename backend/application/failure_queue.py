from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.infrastructure.models import FailureRecord


def record_failure(
    session: Session,
    *,
    tenant_id: UUID,
    operation: str,
    payload: dict[str, Any],
    error: Exception,
    attempts: int = 1,
) -> FailureRecord:
    if attempts < 1:
        raise ValueError("attempt count must be positive")
    delay = min(3600, 2 ** min(attempts, 10))
    record = FailureRecord(
        tenant_id=tenant_id,
        operation=operation,
        payload=payload,
        error_class=type(error).__name__,
        attempts=attempts,
        status="DEAD_LETTER" if attempts >= 5 else "PENDING_RETRY",
        next_retry_at=None if attempts >= 5 else datetime.now(UTC) + timedelta(seconds=delay),
    )
    session.add(record)
    return record


def mark_recovered(record: FailureRecord) -> None:
    record.status = "RECOVERED"
    record.next_retry_at = None
