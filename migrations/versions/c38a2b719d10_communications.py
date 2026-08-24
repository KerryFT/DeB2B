"""normalized communications

Revision ID: c38a2b719d10
Revises: b27f5aa41c02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c38a2b719d10"
down_revision = "b27f5aa41c02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "communications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("thread_id", sa.String(300), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("sender", sa.String(320), nullable=False),
        sa.Column("recipients", postgresql.JSONB(), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", "external_id"),
    )
    op.create_index("ix_communications_tenant_id", "communications", ["tenant_id"])
    op.create_table(
        "communication_attachments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("communication_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["communication_id"], ["communications.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "communication_id", "external_id"),
    )
    op.create_index(
        "ix_communication_attachments_tenant_id", "communication_attachments", ["tenant_id"]
    )
    for table in ("communications", "communication_attachments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
            "WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ar_app")


def downgrade() -> None:
    op.drop_table("communication_attachments")
    op.drop_table("communications")
