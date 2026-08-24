from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database import Base


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class TenantOwned:
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = uuid_pk()
    issuer: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    email: Mapped[str] = mapped_column(String(320))
    __table_args__ = (UniqueConstraint("issuer", "subject"),)


class Membership(Base, TenantOwned):
    __tablename__ = "memberships"
    id: Mapped[UUID] = uuid_pk()
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30))
    __table_args__ = (UniqueConstraint("tenant_id", "user_id"),)


class Customer(Base, TenantOwned):
    __tablename__ = "customers"
    id: Mapped[UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(300))
    tax_id: Mapped[str | None] = mapped_column(String(40))
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)


class Invoice(Base, TenantOwned):
    __tablename__ = "invoices"
    id: Mapped[UUID] = uuid_pk()
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("customers.id"))
    invoice_number: Mapped[str] = mapped_column(String(100))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    outstanding_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    source_fingerprint: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="ck_invoice_amount_nonnegative"),
        CheckConstraint(
            "outstanding_minor >= 0 AND outstanding_minor <= amount_minor",
            name="ck_invoice_outstanding_range",
        ),
        UniqueConstraint("tenant_id", "source_fingerprint"),
        Index("ix_invoice_tenant_due", "tenant_id", "due_date"),
    )


class PaymentCase(Base, TenantOwned):
    __tablename__ = "payment_cases"
    id: Mapped[UUID] = uuid_pk()
    status: Mapped[str] = mapped_column(String(40), default="IMPORTED")
    version: Mapped[int] = mapped_column(Integer, default=1)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_case_queue", "tenant_id", "status", "next_action_at"),)


class CaseInvoice(Base, TenantOwned):
    __tablename__ = "case_invoices"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("invoices.id"))
    __table_args__ = (UniqueConstraint("tenant_id", "case_id", "invoice_id"),)


class Document(Base, TenantOwned):
    __tablename__ = "documents"
    id: Mapped[UUID] = uuid_pk()
    sha256: Mapped[str] = mapped_column(String(64))
    object_key: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[str | None] = mapped_column(String(60))
    pipeline_version: Mapped[str] = mapped_column(String(80), default="native-v1")
    __table_args__ = (UniqueConstraint("tenant_id", "sha256"),)


class DocumentSource(Base, TenantOwned):
    __tablename__ = "document_sources"
    id: Mapped[UUID] = uuid_pk()
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    filename: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(40), default="UPLOAD")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class CaseDocument(Base, TenantOwned):
    __tablename__ = "case_documents"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    purpose: Mapped[str] = mapped_column(String(60), default="SUPPORTING_EVIDENCE")
    __table_args__ = (UniqueConstraint("tenant_id", "case_id", "document_id"),)


class EvidenceSpan(Base, TenantOwned):
    __tablename__ = "evidence_spans"
    id: Mapped[UUID] = uuid_pk()
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    field_name: Mapped[str] = mapped_column(String(100))
    page: Mapped[int | None] = mapped_column(Integer)
    sheet: Mapped[str | None] = mapped_column(String(100))
    cell_range: Mapped[str | None] = mapped_column(String(50))
    polygon: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    quote: Mapped[str] = mapped_column(Text)


class Communication(Base, TenantOwned):
    __tablename__ = "communications"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30), default="gmail")
    external_id: Mapped[str] = mapped_column(String(300))
    thread_id: Mapped[str] = mapped_column(String(300))
    direction: Mapped[str] = mapped_column(String(20))
    sender: Mapped[str] = mapped_column(String(320))
    recipients: Mapped[list[str]] = mapped_column(JSONB, default=list)
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "external_id"),)


class CommunicationAttachment(Base, TenantOwned):
    __tablename__ = "communication_attachments"
    id: Mapped[UUID] = uuid_pk()
    communication_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("communications.id")
    )
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("documents.id"))
    external_id: Mapped[str] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("tenant_id", "communication_id", "external_id"),)


class ConnectorCredential(Base, TenantOwned):
    __tablename__ = "connector_credentials"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    account: Mapped[str] = mapped_column(String(320))
    ciphertext: Mapped[str] = mapped_column(Text)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="CONNECTED")
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "account"),)


class ConnectorCursor(Base, TenantOwned):
    __tablename__ = "connector_cursors"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    account: Mapped[str] = mapped_column(String(320))
    cursor: Mapped[str | None] = mapped_column(String(300))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watch_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="INITIAL_SYNC")
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "account"),)


class BankTransaction(Base, TenantOwned):
    __tablename__ = "bank_transactions"
    id: Mapped[UUID] = uuid_pk()
    external_id: Mapped[str | None] = mapped_column(String(200))
    booked_date: Mapped[date] = mapped_column(Date)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    reference: Mapped[str] = mapped_column(String(500))
    source_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="UNMATCHED")
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_bank_transaction_amount_positive"),
        UniqueConstraint("tenant_id", "source_fingerprint"),
    )


class PaymentAllocation(Base, TenantOwned):
    __tablename__ = "payment_allocations"
    id: Mapped[UUID] = uuid_pk()
    transaction_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bank_transactions.id")
    )
    invoice_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("invoices.id"))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="PROPOSED")
    confirmed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_payment_allocation_amount_positive"),
        UniqueConstraint("tenant_id", "transaction_id", "invoice_id"),
    )


class FailureRecord(Base, TenantOwned):
    __tablename__ = "failure_records"
    id: Mapped[UUID] = uuid_pk()
    operation: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    error_class: Mapped[str] = mapped_column(String(200))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="PENDING_RETRY")
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Blocker(Base, TenantOwned):
    __tablename__ = "blockers"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    blocker_type: Mapped[str] = mapped_column(String(80))
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Approval(Base, TenantOwned):
    __tablename__ = "approvals"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class DraftAction(Base, TenantOwned):
    __tablename__ = "draft_actions"
    id: Mapped[UUID] = uuid_pk()
    approval_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("approvals.id"))
    idempotency_key: Mapped[str] = mapped_column(String(300))
    external_draft_id: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)


class AuditEntry(Base, TenantOwned):
    __tablename__ = "audit_entries"
    id: Mapped[UUID] = uuid_pk()
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    actor_type: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str | None] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(100))
    aggregate_type: Mapped[str] = mapped_column(String(50))
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    correlation_id: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class OutboxEvent(Base, TenantOwned):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = uuid_pk()
    topic: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(Base, TenantOwned):
    __tablename__ = "idempotency_records"
    id: Mapped[UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String(300))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_code: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("tenant_id", "key"),)
