"""case document links

Revision ID: d49c2e8fa311
Revises: c38a2b719d10
"""

import sqlalchemy as sa
from alembic import op

revision = "d49c2e8fa311"
down_revision = "c38a2b719d10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.String(60), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["payment_cases.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "case_id", "document_id"),
    )
    op.create_index("ix_case_documents_tenant_id", "case_documents", ["tenant_id"])
    op.execute("ALTER TABLE case_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE case_documents FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_case_documents ON case_documents "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON case_documents TO ar_app")


def downgrade() -> None:
    op.drop_table("case_documents")
