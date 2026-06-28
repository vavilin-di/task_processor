"""alter_outbox_messages_fields

Revision ID: 6ecb6140647f
Revises: 0341e742d50e
Create Date: 2026-06-29 00:00:39.273765

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6ecb6140647f"
down_revision: str | Sequence[str] | None = "0341e742d50e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.alter_column(
            "errors",
            existing_type=postgresql.JSON(astext_type=sa.Text()),
            type_=sa.ARRAY(sa.String()),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("outbox_messages", schema=None) as batch_op:
        batch_op.alter_column(
            "errors",
            existing_type=sa.ARRAY(sa.String()),
            type_=postgresql.JSON(astext_type=sa.Text()),
            existing_nullable=False,
        )
