from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.infrastructure.models import AuditEntry, OutboxEvent


@dataclass(frozen=True, slots=True)
class MutationContext:
    tenant_id: UUID
    actor_type: str
    actor_id: str | None
    correlation_id: str


def record_mutation(
    session: Session,
    *,
    context: MutationContext,
    action: str,
    aggregate_type: str,
    aggregate_id: UUID,
    audit_payload: dict[str, Any],
    event_topic: str,
    event_payload: dict[str, Any],
) -> UUID:
    """Add audit and outbox records to the caller's existing transaction."""
    event_id = uuid4()
    session.add(
        AuditEntry(
            tenant_id=context.tenant_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            action=action,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            correlation_id=context.correlation_id,
            payload=audit_payload,
        )
    )
    session.add(
        OutboxEvent(
            id=event_id,
            tenant_id=context.tenant_id,
            topic=event_topic,
            payload=event_payload,
        )
    )
    return event_id
