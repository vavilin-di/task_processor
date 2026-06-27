"""tasks_outbox_messages_alter

Revision ID: 6188ca6a09bb
Revises: c97449149006
Create Date: 2026-06-27 23:36:59.392040

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6188ca6a09bb"
down_revision: str | Sequence[str] | None = "f65ad40b16f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payload", sa.JSON(), nullable=False))
        batch_op.alter_column("started_at", existing_type=postgresql.TIMESTAMP(), server_default=None, nullable=True)

    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f("outbox_messages_aggregate_id_fkey"), type_="foreignkey")
        batch_op.create_foreign_key(
            "outbox_messages_aggregate_id_fkey", "tasks", ["aggregate_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.alter_column(
            "started_at", existing_type=postgresql.TIMESTAMP(), server_default=sa.text("now()"), nullable=False
        )
        batch_op.drop_column("payload")

    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.drop_constraint("outbox_messages_aggregate_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(batch_op.f("outbox_messages_aggregate_id_fkey"), "tasks", ["aggregate_id"], ["id"])
