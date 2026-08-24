"""failure recovery queue

Revision ID: b81f43e9f755
Revises: a70e32d8e644
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b81f43e9f755"
down_revision = "a70e32d8e644"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "failure_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("error_class", sa.String(200), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_failure_records_tenant_id", "failure_records", ["tenant_id"])
    op.execute("ALTER TABLE failure_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE failure_records FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation_failure_records ON failure_records "
        "USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON failure_records TO ar_app")


def downgrade() -> None:
    op.drop_table("failure_records")
