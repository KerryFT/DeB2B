"""document source provenance

Revision ID: b27f5aa41c02
Revises: eaaa5b2a4560
"""

import sqlalchemy as sa
from alembic import op

revision = "b27f5aa41c02"
down_revision = "eaaa5b2a4560"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_sources_tenant_id", "document_sources", ["tenant_id"])
    op.execute("ALTER TABLE document_sources ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_sources FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_document_sources ON document_sources "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON document_sources TO ar_app")


def downgrade() -> None:
    op.drop_index("ix_document_sources_tenant_id", table_name="document_sources")
    op.drop_table("document_sources")
