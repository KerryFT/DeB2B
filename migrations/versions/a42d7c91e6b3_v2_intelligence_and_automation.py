"""V2 point-in-time intelligence and safe automation storage.

Revision ID: a42d7c91e6b3
Revises: f19c7a4d2e10

All changes are additive. Existing invoices receive a nullable account owner; derived data is
backfilled by idempotent jobs after deployment. Roll forward is preferred. Before downgrade,
disable automation and stop derived-data writers; action history is otherwise intentionally kept.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a42d7c91e6b3"
down_revision = "f19c7a4d2e10"
branch_labels = None
depends_on = None

TENANT_TABLES = (
    "feature_definitions",
    "feature_snapshots",
    "model_registry",
    "prediction_runs",
    "prediction_records",
    "automation_policies",
    "automation_decisions",
    "dispute_root_causes",
    "escalation_recommendations",
    "customer_behavior_snapshots",
    "account_manager_benchmarks",
    "derived_job_runs",
)


def tenant_column() -> sa.Column:
    return sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id"), nullable=False)


def json(nullable: bool = False) -> sa.Column:
    return sa.Column("payload", postgresql.JSONB(), nullable=nullable)


def upgrade() -> None:
    op.add_column("invoices", sa.Column("account_owner", sa.String(320)))
    op.create_table(
        "feature_definitions",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("schema", postgresql.JSONB(), nullable=False),
        sa.Column("point_in_time_policy", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.UniqueConstraint("tenant_id", "name", "version"),
    )
    op.create_table(
        "feature_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(200), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(100), nullable=False),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("data_quality", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "entity_type", "entity_id", "as_of", "feature_version"),
    )
    op.create_table(
        "model_registry",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CHALLENGER"),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.Column("feature_version", sa.String(100), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("trained_through", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "task_type", "model_name", "model_version"),
    )
    op.create_table(
        "prediction_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("feature_version", sa.String(100), nullable=False),
        sa.Column("dataset_version", sa.String(100), nullable=False),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "prediction_records",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("run_id", sa.UUID(), sa.ForeignKey("prediction_runs.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(200), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(50), nullable=False),
        sa.Column("lower_value", sa.String(50)),
        sa.Column("upper_value", sa.String(50)),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False),
        sa.Column("feature_snapshot_id", sa.UUID(), sa.ForeignKey("feature_snapshots.id")),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "run_id", "entity_type", "entity_id", "horizon_days"),
    )
    op.create_table(
        "automation_policies",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id")),
        sa.Column("mode", sa.String(20), nullable=False, server_default="disabled"),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("kill_switch", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled_by", sa.UUID()),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "customer_id", "policy_version"),
    )
    op.create_table(
        "automation_decisions",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("case_id", sa.UUID(), sa.ForeignKey("payment_cases.id"), nullable=False),
        sa.Column("policy_id", sa.UUID(), sa.ForeignKey("automation_policies.id"), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("case_version", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(30), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("exclusions", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("external_id", sa.String(300)),
        sa.Column("delivery_status", sa.String(30), nullable=False, server_default="NOT_SENT"),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )
    op.create_table(
        "dispute_root_causes",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("case_id", sa.UUID(), sa.ForeignKey("payment_cases.id"), nullable=False),
        sa.Column("primary_cause", sa.String(80), nullable=False),
        sa.Column("contributing_causes", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.String(30), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False),
        sa.Column("taxonomy_version", sa.String(100), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("corrected_by", sa.UUID()),
    )
    op.create_table(
        "escalation_recommendations",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("case_id", sa.UUID(), sa.ForeignKey("payment_cases.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(80), nullable=False),
        sa.Column("rationale", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.String(30), nullable=False),
        sa.Column("rule_version", sa.String(100), nullable=False),
        sa.Column("feedback", sa.String(30)),
        sa.Column("feedback_by", sa.UUID()),
    )
    op.create_table(
        "customer_behavior_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("profile_version", sa.String(100), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("segment", sa.String(50), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("data_quality", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "customer_id", "as_of", "window_days", "profile_version"),
    )
    op.create_table(
        "account_manager_benchmarks",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("manager_id", sa.String(200), nullable=False),
        sa.Column("team_id", sa.String(200)),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("metric_version", sa.String(100), nullable=False),
        sa.Column("raw_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("adjusted_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("uncertainty", postgresql.JSONB(), nullable=False),
        sa.Column("suppressed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "manager_id", "as_of", "window_days", "metric_version"),
    )
    op.create_table(
        "derived_job_runs",
        sa.Column("id", sa.UUID(), primary_key=True),
        tenant_column(),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("checkpoint", sa.String(300), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_class", sa.String(100)),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
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
    op.drop_column("invoices", "account_owner")
