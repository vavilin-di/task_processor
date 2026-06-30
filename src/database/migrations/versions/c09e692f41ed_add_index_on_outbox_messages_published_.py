"""add_index_on_outbox_messages_published_created_at

Revision ID: c09e692f41ed
Revises: 6ecb6140647f
Create Date: 2026-06-29 15:53:48.216427

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c09e692f41ed"
down_revision: str | Sequence[str] | None = "6ecb6140647f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "outbox_messages_published_created_at_idx",
        "outbox_messages",
        ["is_published", "created_at"],
        postgresql_where=sa.text("is_published = true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_outbox_messages_published_created")
