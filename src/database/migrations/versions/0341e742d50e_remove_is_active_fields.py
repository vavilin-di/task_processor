"""remove_is_active_fields_and_set_error_message_not_null

Revision ID: 0341e742d50e
Revises: c97449149006
Create Date: 2026-06-28 03:28:40.269507

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0341e742d50e"
down_revision: str | Sequence[str] | None = "c97449149006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("dlq_messages", schema=None) as batch_op:
        batch_op.alter_column("error_message", existing_type=sa.TEXT(), nullable=False)
        batch_op.drop_column("is_active")

    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.drop_column("is_active")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.BOOLEAN(), server_default=sa.text("true"), autoincrement=False, nullable=False)
        )

    with op.batch_alter_table("dlq_messages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.BOOLEAN(), server_default=sa.text("true"), autoincrement=False, nullable=False)
        )
        batch_op.alter_column("error_message", existing_type=sa.TEXT(), nullable=True)
