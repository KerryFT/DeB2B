"""portfolio sessions and durable connector cursors

Revision ID: c7a8e4b1d902
Revises: a42d7c91e6b3
"""

import sqlalchemy as sa
from alembic import op

revision = "c7a8e4b1d902"
down_revision = "a42d7c91e6b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_portfolio_sessions_expires_at", "portfolio_sessions", ["expires_at"])
    op.alter_column(
        "connector_cursors",
        "cursor",
        existing_type=sa.String(length=300),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "connector_cursors",
        "cursor",
        existing_type=sa.Text(),
        type_=sa.String(length=300),
        existing_nullable=True,
    )
    op.drop_index("ix_portfolio_sessions_expires_at", table_name="portfolio_sessions")
    op.drop_table("portfolio_sessions")
