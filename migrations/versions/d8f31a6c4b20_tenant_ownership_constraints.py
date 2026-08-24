"""enforce tenant ownership across relational links

Revision ID: d8f31a6c4b20
Revises: c7a8e4b1d902
"""

from alembic import op

revision = "d8f31a6c4b20"
down_revision = "c7a8e4b1d902"
branch_labels = None
depends_on = None

PARENTS = (
    "customers",
    "payment_cases",
    "invoices",
    "documents",
    "communications",
    "bank_transactions",
    "approvals",
    "bulk_approval_batches",
    "prediction_runs",
    "feature_snapshots",
    "automation_policies",
)

RELATIONSHIPS = (
    ("invoices", "customer_id", "customers"),
    ("case_invoices", "case_id", "payment_cases"),
    ("case_invoices", "invoice_id", "invoices"),
    ("document_sources", "document_id", "documents"),
    ("case_documents", "case_id", "payment_cases"),
    ("case_documents", "document_id", "documents"),
    ("evidence_spans", "document_id", "documents"),
    ("communication_attachments", "communication_id", "communications"),
    ("communication_attachments", "document_id", "documents"),
    ("bank_transactions", "reversal_of_id", "bank_transactions"),
    ("payment_allocations", "transaction_id", "bank_transactions"),
    ("payment_allocations", "invoice_id", "invoices"),
    ("blockers", "case_id", "payment_cases"),
    ("approvals", "case_id", "payment_cases"),
    ("draft_actions", "approval_id", "approvals"),
    ("payment_rules", "customer_id", "customers"),
    ("notification_actions", "approval_id", "approvals"),
    ("bulk_approval_items", "batch_id", "bulk_approval_batches"),
    ("bulk_approval_items", "approval_id", "approvals"),
    ("prediction_records", "run_id", "prediction_runs"),
    ("prediction_records", "feature_snapshot_id", "feature_snapshots"),
    ("automation_policies", "customer_id", "customers"),
    ("automation_decisions", "case_id", "payment_cases"),
    ("automation_decisions", "policy_id", "automation_policies"),
    ("dispute_root_causes", "case_id", "payment_cases"),
    ("escalation_recommendations", "case_id", "payment_cases"),
    ("customer_behavior_snapshots", "customer_id", "customers"),
)


def upgrade() -> None:
    for table in PARENTS:
        op.create_unique_constraint(f"uq_{table}_tenant_id_id", table, ["tenant_id", "id"])
    for child, column, parent in RELATIONSHIPS:
        op.create_foreign_key(
            f"fk_{child}_tenant_{column}",
            child,
            parent,
            ["tenant_id", column],
            ["tenant_id", "id"],
        )


def downgrade() -> None:
    for child, column, _parent in reversed(RELATIONSHIPS):
        op.drop_constraint(f"fk_{child}_tenant_{column}", child, type_="foreignkey")
    for table in reversed(PARENTS):
        op.drop_constraint(f"uq_{table}_tenant_id_id", table, type_="unique")
