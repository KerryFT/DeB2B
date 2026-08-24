from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.ports import DraftSpec, GmailPort
from backend.infrastructure.models import Approval, DraftAction, OutboxEvent


async def create_approved_draft(
    session: Session,
    *,
    approval: Approval,
    idempotency_key: str,
    spec: DraftSpec,
    gmail: GmailPort,
) -> DraftAction:
    if approval.status != "APPROVED":
        raise PermissionError("approved content is required")
    existing = session.scalar(
        select(DraftAction).where(
            DraftAction.tenant_id == approval.tenant_id,
            DraftAction.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    external_id = await gmail.create_draft(idempotency_key=idempotency_key, spec=spec)
    action = DraftAction(
        tenant_id=approval.tenant_id,
        approval_id=approval.id,
        idempotency_key=idempotency_key,
        external_draft_id=external_id,
        status="CREATED",
    )
    session.add(action)
    session.flush()
    session.add(
        OutboxEvent(
            tenant_id=approval.tenant_id,
            topic="gmail.draft.created.v1",
            payload={
                "draft_action_id": str(action.id),
                "external_draft_id": external_id,
                "approval_id": str(approval.id),
            },
        )
    )
    return action
