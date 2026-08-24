"""gmail connector state

Revision ID: f6bd21c7d533
Revises: e5ac10b6c422
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f6bd21c7d533"
down_revision = "e5ac10b6c422"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("account", sa.String(320), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", "account"),
    )
    op.create_index("ix_connector_credentials_tenant_id", "connector_credentials", ["tenant_id"])
    op.create_table(
        "connector_cursors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("account", sa.String(320), nullable=False),
        sa.Column("cursor", sa.String(300)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("watch_expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", "account"),
    )
    op.create_index("ix_connector_cursors_tenant_id", "connector_cursors", ["tenant_id"])
    for table in ("connector_credentials", "connector_cursors"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {table} "
            "USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
            "WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ar_app")


def downgrade() -> None:
    op.drop_table("connector_cursors")
    op.drop_table("connector_credentials")
