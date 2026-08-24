from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.application.approvals import approve_content, content_hash
from backend.application.draft_effect import create_approved_draft
from backend.application.gmail_fixture import FixtureMessage, ingest_fixture_message
from backend.application.ports import DraftSpec
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.fakes import FakeGmail
from backend.infrastructure.models import (
    Approval,
    Communication,
    DraftAction,
    OutboxEvent,
    PaymentCase,
    Tenant,
)


@pytest.mark.asyncio
async def test_fixture_replay_approval_and_draft_are_idempotent() -> None:
    tenant_id, actor_id = uuid4(), uuid4()
    body = "Vui lòng xác nhận chứng từ nghiệm thu INV-2026-0001."
    message = FixtureMessage(
        external_id="gmail-fixture-1",
        thread_id="thread-1",
        direction="INBOUND",
        sender="customer@example.com",
        recipients=["ar@example.com"],
        subject="Re: INV-2026-0001",
        body="Chưa nhận được biên bản nghiệm thu.",
        received_at=datetime.now(UTC),
    )
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Vertical slice"))
        session.flush()
        case = PaymentCase(tenant_id=tenant_id, status="AWAITING_APPROVAL")
        session.add(case)
        session.flush()
        approval = Approval(
            tenant_id=tenant_id,
            case_id=case.id,
            content_hash=content_hash(body),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(approval)
        session.flush()
        approval_id = approval.id
        assert ingest_fixture_message(session, tenant_id=tenant_id, message=message)
    with SessionFactory.begin() as session:
        assert not ingest_fixture_message(session, tenant_id=tenant_id, message=message)
        assert (
            session.scalar(
                select(func.count())
                .select_from(Communication)
                .where(Communication.tenant_id == tenant_id)
            )
            == 1
        )
        approved = approve_content(
            session,
            tenant_id=tenant_id,
            approval_id=approval_id,
            actor_id=actor_id,
            role="approver",
            current_content=body,
        )
        gmail = FakeGmail()
        spec = DraftSpec(
            to=("customer@example.com",),
            cc=(),
            subject="INV-2026-0001",
            body=body,
        )
        first = await create_approved_draft(
            session,
            approval=approved,
            idempotency_key="draft-once",
            spec=spec,
            gmail=gmail,
        )
        second = await create_approved_draft(
            session,
            approval=approved,
            idempotency_key="draft-once",
            spec=spec,
            gmail=gmail,
        )
        assert first.id == second.id
        assert session.scalar(select(func.count()).select_from(DraftAction)) >= 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(
                    OutboxEvent.tenant_id == tenant_id,
                    OutboxEvent.topic == "gmail.draft.created.v1",
                )
            )
            == 1
        )
        assert len(gmail.drafts) == 1


def test_changed_content_invalidates_approval_and_wrong_role_is_rejected() -> None:
    tenant_id, actor_id = uuid4(), uuid4()
    with SessionFactory.begin() as session:
        session.add(Tenant(id=tenant_id, name="Approval guardrail"))
        session.flush()
        case = PaymentCase(tenant_id=tenant_id)
        session.add(case)
        session.flush()
        approval = Approval(
            tenant_id=tenant_id,
            case_id=case.id,
            content_hash=content_hash("original"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(approval)
        session.flush()
        with pytest.raises(PermissionError):
            approve_content(
                session,
                tenant_id=tenant_id,
                approval_id=approval.id,
                actor_id=actor_id,
                role="operator",
                current_content="original",
            )
        with pytest.raises(ValueError, match="content changed"):
            approve_content(
                session,
                tenant_id=tenant_id,
                approval_id=approval.id,
                actor_id=actor_id,
                role="approver",
                current_content="edited",
            )
        assert approval.status == "INVALIDATED"
