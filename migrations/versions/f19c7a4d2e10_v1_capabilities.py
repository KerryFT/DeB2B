"""V1 capability storage

Revision ID: f19c7a4d2e10
Revises: b81f43e9f755

Production note: all operations create new tables and indexes; no existing tenant table is
rewritten. Backfill is performed by opt-in sync/forecast jobs after deploy. Roll forward is the
preferred recovery; downgrade drops only empty/new V1 tables after writers are stopped.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f19c7a4d2e10"
down_revision = "b81f43e9f755"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "connector_configs",
    "external_record_maps",
    "inbox_events",
    "payment_rules",
    "zalo_templates",
    "notification_actions",
    "bulk_approval_batches",
    "bulk_approval_items",
    "forecast_snapshots",
    "llm_usage_events",
    "llm_quality_metrics",
)


def tenant_columns() -> list[sa.Column]:
    return [sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False)]


def upgrade() -> None:
    op.add_column(
        "bank_transactions",
        sa.Column("transaction_type", sa.String(30), nullable=False, server_default="CREDIT"),
    )
    op.add_column("bank_transactions", sa.Column("reversal_of_id", sa.UUID()))
    op.create_foreign_key(
        "fk_bank_transactions_reversal_of",
        "bank_transactions",
        "bank_transactions",
        ["reversal_of_id"],
        ["id"],
    )
    op.add_column(
        "bank_transactions",
        sa.Column("correction_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("payment_allocations", sa.Column("reversed_by", sa.UUID()))
    op.add_column("payment_allocations", sa.Column("reversal_reason", sa.String(500)))
    op.create_table(
        "connector_configs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("environment", sa.String(30), nullable=False),
        sa.Column("secret_reference", sa.String(500), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "provider"),
    )
    op.create_table(
        "external_record_maps",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("external_version", sa.String(100), nullable=False),
        sa.Column("canonical_type", sa.String(50), nullable=False),
        sa.Column("canonical_id", sa.UUID(), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        *tenant_columns(),
        sa.UniqueConstraint(
            "tenant_id", "provider", "record_type", "external_id", "external_version"
        ),
    )
    op.create_table(
        "inbox_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("external_event_id", sa.String(300), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "provider", "external_event_id"),
    )
    op.create_table(
        "payment_rules",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id")),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("scope", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("published_by", sa.UUID()),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "customer_id", "rule_type", "version"),
    )
    op.create_table(
        "zalo_templates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(20), nullable=False),
        sa.Column("allowed_variables", postgresql.JSONB(), nullable=False),
        sa.Column("policy", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "template_id", "version"),
    )
    op.create_table(
        "notification_actions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("approval_id", sa.UUID(), sa.ForeignKey("approvals.id"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("recipient_id", sa.String(300), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("external_id", sa.String(300)),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )
    op.create_table(
        "bulk_approval_batches",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("filter_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )
    op.create_table(
        "bulk_approval_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("batch_id", sa.UUID(), sa.ForeignKey("bulk_approval_batches.id"), nullable=False),
        sa.Column("approval_id", sa.UUID(), sa.ForeignKey("approvals.id"), nullable=False),
        sa.Column("expected_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(100)),
        *tenant_columns(),
        sa.UniqueConstraint("tenant_id", "batch_id", "approval_id"),
    )
    op.create_table(
        "forecast_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(100), nullable=False),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("predictions", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        *tenant_columns(),
    )
    op.create_table(
        "llm_pricing",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("input_per_million", sa.String(40), nullable=False),
        sa.Column("output_per_million", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("provider", "model", "effective_from", "version"),
    )
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("route", sa.String(100), nullable=False),
        sa.Column("fallback", sa.Boolean(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("schema_valid", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("request_metadata", postgresql.JSONB(), nullable=False),
        *tenant_columns(),
    )
    op.create_table(
        "llm_quality_metrics",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.String(50), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        *tenant_columns(),
    )
    tenant_expr = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    for table in TENANT_TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            f"USING ({tenant_expr}) WITH CHECK ({tenant_expr})"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ar_app")


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.drop_table(table)
    op.drop_table("llm_pricing")
    op.drop_column("payment_allocations", "reversal_reason")
    op.drop_column("payment_allocations", "reversed_by")
    op.drop_column("bank_transactions", "correction_version")
    op.drop_constraint("fk_bank_transactions_reversal_of", "bank_transactions", type_="foreignkey")
    op.drop_column("bank_transactions", "reversal_of_id")
    op.drop_column("bank_transactions", "transaction_type")
