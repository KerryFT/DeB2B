from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.models import Communication, CommunicationAttachment


class FixtureAttachment(BaseModel):
    external_id: str = Field(min_length=1)
    document_id: UUID


class FixtureMessage(BaseModel):
    external_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    direction: str = Field(pattern="^(INBOUND|OUTBOUND)$")
    sender: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    recipients: list[str]
    subject: str
    body: str
    received_at: datetime
    attachments: list[FixtureAttachment] = Field(default_factory=list)


def ingest_fixture_message(session: Session, *, tenant_id: UUID, message: FixtureMessage) -> bool:
    existing = session.scalar(
        select(Communication).where(
            Communication.tenant_id == tenant_id,
            Communication.provider == "gmail-fixture",
            Communication.external_id == message.external_id,
        )
    )
    if existing is not None:
        return False
    communication = Communication(
        tenant_id=tenant_id,
        provider="gmail-fixture",
        external_id=message.external_id,
        thread_id=message.thread_id,
        direction=message.direction,
        sender=str(message.sender),
        recipients=[str(value) for value in message.recipients],
        subject=message.subject,
        body=message.body,
        received_at=message.received_at,
    )
    session.add(communication)
    session.flush()
    session.add_all(
        CommunicationAttachment(
            tenant_id=tenant_id,
            communication_id=communication.id,
            document_id=attachment.document_id,
            external_id=attachment.external_id,
        )
        for attachment in message.attachments
    )
    return True
