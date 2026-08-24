"""tenant scoped draft idempotency

Revision ID: e5ac10b6c422
Revises: d49c2e8fa311
"""

from alembic import op

revision = "e5ac10b6c422"
down_revision = "d49c2e8fa311"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("draft_actions_idempotency_key_key", "draft_actions", type_="unique")
    op.create_unique_constraint(
        "uq_draft_actions_tenant_idempotency", "draft_actions", ["tenant_id", "idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_draft_actions_tenant_idempotency", "draft_actions", type_="unique")
    op.create_unique_constraint(
        "draft_actions_idempotency_key_key", "draft_actions", ["idempotency_key"]
    )
