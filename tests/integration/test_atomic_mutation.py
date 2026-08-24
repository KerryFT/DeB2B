from uuid import uuid4

from sqlalchemy import func, select

from backend.application.idempotency import (
    StoredResponse,
    find_stored_response,
    store_response,
)
from backend.application.mutation import MutationContext, record_mutation
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import AuditEntry, OutboxEvent, Tenant


def test_audit_outbox_and_idempotent_response_commit_together() -> None:
    tenant_id, aggregate_id = uuid4(), uuid4()
    request = {"case_id": str(aggregate_id), "action": "review"}
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Atomic"))
        session.flush()
        event_id = record_mutation(
            session,
            context=MutationContext(tenant_id, "USER", "test", "corr-1"),
            action="CASE_REVIEWED",
            aggregate_type="CASE",
            aggregate_id=aggregate_id,
            audit_payload={"decision": "confirmed"},
            event_topic="case.reviewed.v1",
            event_payload={"case_id": str(aggregate_id)},
        )
        store_response(
            session,
            tenant_id=tenant_id,
            key="review-once",
            request=request,
            response=StoredResponse(200, {"event_id": str(event_id)}),
        )

    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(AuditEntry)) >= 1
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) >= 1
        stored = find_stored_response(
            session, tenant_id=tenant_id, key="review-once", payload=request
        )
        assert stored is not None
        assert stored.body == {"event_id": str(event_id)}
