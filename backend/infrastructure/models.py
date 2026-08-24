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


class PortfolioSession(Base):
    __tablename__ = "portfolio_sessions"
    id: Mapped[UUID] = uuid_pk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"))
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
    account_owner: Mapped[str | None] = mapped_column(String(320))
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
    cursor: Mapped[str | None] = mapped_column(Text)
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
    transaction_type: Mapped[str] = mapped_column(String(30), default="CREDIT")
    reversal_of_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bank_transactions.id")
    )
    correction_version: Mapped[int] = mapped_column(Integer, default=1)
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
    reversed_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    reversal_reason: Mapped[str | None] = mapped_column(String(500))
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


class ConnectorConfig(Base, TenantOwned):
    __tablename__ = "connector_configs"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    environment: Mapped[str] = mapped_column(String(30), default="sandbox")
    secret_reference: Mapped[str] = mapped_column(String(500))
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("tenant_id", "provider"),)


class ExternalRecordMap(Base, TenantOwned):
    __tablename__ = "external_record_maps"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    record_type: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(300))
    external_version: Mapped[str] = mapped_column(String(100))
    canonical_type: Mapped[str] = mapped_column(String(50))
    canonical_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "record_type", "external_id", "external_version"),
    )


class InboxEvent(Base, TenantOwned):
    __tablename__ = "inbox_events"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    external_event_id: Mapped[str] = mapped_column(String(300))
    payload_hash: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "external_event_id"),)


class PaymentRule(Base, TenantOwned):
    __tablename__ = "payment_rules"
    id: Mapped[UUID] = uuid_pk()
    customer_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("customers.id")
    )
    rule_type: Mapped[str] = mapped_column(String(50))
    scope: Mapped[str] = mapped_column(String(30))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    effective_from: Mapped[date] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    published_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    __table_args__ = (UniqueConstraint("tenant_id", "customer_id", "rule_type", "version"),)


class ZaloTemplateRecord(Base, TenantOwned):
    __tablename__ = "zalo_templates"
    id: Mapped[UUID] = uuid_pk()
    template_id: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)
    locale: Mapped[str] = mapped_column(String(20))
    allowed_variables: Mapped[list[str]] = mapped_column(JSONB, default=list)
    policy: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    __table_args__ = (UniqueConstraint("tenant_id", "template_id", "version"),)


class NotificationAction(Base, TenantOwned):
    __tablename__ = "notification_actions"
    id: Mapped[UUID] = uuid_pk()
    approval_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("approvals.id"))
    channel: Mapped[str] = mapped_column(String(30))
    recipient_id: Mapped[str] = mapped_column(String(300))
    template_id: Mapped[str] = mapped_column(String(100))
    template_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="PREVIEWED")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    external_id: Mapped[str | None] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)


class BulkApprovalBatch(Base, TenantOwned):
    __tablename__ = "bulk_approval_batches"
    id: Mapped[UUID] = uuid_pk()
    idempotency_key: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), default="PREVIEWED")
    filter_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)


class BulkApprovalItem(Base, TenantOwned):
    __tablename__ = "bulk_approval_items"
    id: Mapped[UUID] = uuid_pk()
    batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("bulk_approval_batches.id")
    )
    approval_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("approvals.id"))
    expected_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("tenant_id", "batch_id", "approval_id"),)


class ForecastSnapshot(Base, TenantOwned):
    __tablename__ = "forecast_snapshots"
    id: Mapped[UUID] = uuid_pk()
    as_of: Mapped[date] = mapped_column(Date)
    horizon_days: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(100))
    rule_version: Mapped[str] = mapped_column(String(100))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    predictions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class LLMPricing(Base):
    __tablename__ = "llm_pricing"
    id: Mapped[UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3))
    input_per_million: Mapped[str] = mapped_column(String(40))
    output_per_million: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("provider", "model", "effective_from", "version"),)


class LLMUsageEvent(Base, TenantOwned):
    __tablename__ = "llm_usage_events"
    id: Mapped[UUID] = uuid_pk()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    task_type: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    route: Mapped[str] = mapped_column(String(100))
    fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    success: Mapped[bool] = mapped_column(Boolean)
    schema_valid: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class LLMQualityMetric(Base, TenantOwned):
    __tablename__ = "llm_quality_metrics"
    id: Mapped[UUID] = uuid_pk()
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dataset_version: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    metric_name: Mapped[str] = mapped_column(String(100))
    metric_value: Mapped[str] = mapped_column(String(50))
    sample_count: Mapped[int] = mapped_column(Integer)


class FeatureDefinition(Base, TenantOwned):
    __tablename__ = "feature_definitions"
    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(100))
    schema: Mapped[dict[str, Any]] = mapped_column(JSONB)
    point_in_time_policy: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    __table_args__ = (UniqueConstraint("tenant_id", "name", "version"),)


class FeatureSnapshot(Base, TenantOwned):
    __tablename__ = "feature_snapshots"
    id: Mapped[UUID] = uuid_pk()
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(200))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    feature_version: Mapped[str] = mapped_column(String(100))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    features: Mapped[dict[str, Any]] = mapped_column(JSONB)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB)
    data_quality: Mapped[list[str]] = mapped_column(JSONB, default=list)
    __table_args__ = (
        UniqueConstraint("tenant_id", "entity_type", "entity_id", "as_of", "feature_version"),
    )


class ModelRegistry(Base, TenantOwned):
    __tablename__ = "model_registry"
    id: Mapped[UUID] = uuid_pk()
    task_type: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="CHALLENGER")
    dataset_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    trained_through: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "task_type", "model_name", "model_version"),)


class PredictionRun(Base, TenantOwned):
    __tablename__ = "prediction_runs"
    id: Mapped[UUID] = uuid_pk()
    run_type: Mapped[str] = mapped_column(String(50))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    horizon_days: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    dataset_version: Mapped[str] = mapped_column(String(100))
    inputs_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class PredictionRecord(Base, TenantOwned):
    __tablename__ = "prediction_records"
    id: Mapped[UUID] = uuid_pk()
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("prediction_runs.id"))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(200))
    horizon_days: Mapped[int] = mapped_column(Integer)
    value: Mapped[str] = mapped_column(String(50))
    lower_value: Mapped[str | None] = mapped_column(String(50))
    upper_value: Mapped[str | None] = mapped_column(String(50))
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    feature_snapshot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("feature_snapshots.id")
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint("tenant_id", "run_id", "entity_type", "entity_id", "horizon_days"),
    )


class AutomationPolicyRecord(Base, TenantOwned):
    __tablename__ = "automation_policies"
    id: Mapped[UUID] = uuid_pk()
    customer_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("customers.id")
    )
    mode: Mapped[str] = mapped_column(String(20), default="disabled")
    policy_version: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("tenant_id", "customer_id", "policy_version"),)


class AutomationDecisionRecord(Base, TenantOwned):
    __tablename__ = "automation_decisions"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    policy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("automation_policies.id")
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    case_version: Mapped[int] = mapped_column(Integer)
    disposition: Mapped[str] = mapped_column(String(30))
    eligible: Mapped[bool] = mapped_column(Boolean)
    exclusions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    idempotency_key: Mapped[str] = mapped_column(String(300))
    external_id: Mapped[str | None] = mapped_column(String(300))
    delivery_status: Mapped[str] = mapped_column(String(30), default="NOT_SENT")
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)


class DisputeRootCauseRecord(Base, TenantOwned):
    __tablename__ = "dispute_root_causes"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    primary_cause: Mapped[str] = mapped_column(String(80))
    contributing_causes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    confidence: Mapped[str] = mapped_column(String(30))
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    taxonomy_version: Mapped[str] = mapped_column(String(100))
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    owner_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reopen_count: Mapped[int] = mapped_column(Integer, default=0)
    corrected_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class EscalationRecommendationRecord(Base, TenantOwned):
    __tablename__ = "escalation_recommendations"
    id: Mapped[UUID] = uuid_pk()
    case_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("payment_cases.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rank: Mapped[int] = mapped_column(Integer)
    strategy: Mapped[str] = mapped_column(String(80))
    rationale: Mapped[dict[str, Any]] = mapped_column(JSONB)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    confidence: Mapped[str] = mapped_column(String(30))
    rule_version: Mapped[str] = mapped_column(String(100))
    feedback: Mapped[str | None] = mapped_column(String(30))
    feedback_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))


class CustomerBehaviorSnapshot(Base, TenantOwned):
    __tablename__ = "customer_behavior_snapshots"
    id: Mapped[UUID] = uuid_pk()
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("customers.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_days: Mapped[int] = mapped_column(Integer)
    profile_version: Mapped[str] = mapped_column(String(100))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    segment: Mapped[str] = mapped_column(String(50))
    sample_size: Mapped[int] = mapped_column(Integer)
    data_quality: Mapped[list[str]] = mapped_column(JSONB, default=list)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", "as_of", "window_days", "profile_version"),
    )


class AccountManagerBenchmarkSnapshot(Base, TenantOwned):
    __tablename__ = "account_manager_benchmarks"
    id: Mapped[UUID] = uuid_pk()
    manager_id: Mapped[str] = mapped_column(String(200))
    team_id: Mapped[str | None] = mapped_column(String(200))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_days: Mapped[int] = mapped_column(Integer)
    metric_version: Mapped[str] = mapped_column(String(100))
    raw_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    adjusted_metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    sample_size: Mapped[int] = mapped_column(Integer)
    uncertainty: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    suppressed: Mapped[bool] = mapped_column(Boolean, default=True)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint("tenant_id", "manager_id", "as_of", "window_days", "metric_version"),
    )


class DerivedJobRun(Base, TenantOwned):
    __tablename__ = "derived_job_runs"
    id: Mapped[UUID] = uuid_pk()
    job_type: Mapped[str] = mapped_column(String(100))
    checkpoint: Mapped[str] = mapped_column(String(300))
    idempotency_key: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_class: Mapped[str | None] = mapped_column(String(100))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key"),)
