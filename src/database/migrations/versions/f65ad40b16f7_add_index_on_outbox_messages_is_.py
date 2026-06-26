"""add index on outbox_messages.is_published=False

Revision ID: f65ad40b16f7
Revises: ac0854310213
Create Date: 2026-06-16 02:11:37.123089

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f65ad40b16f7"
down_revision: str | Sequence[str] | None = "ac0854310213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "outbox_messages_not_published_idx",
        "outbox_messages",
        ["created_at"],
        postgresql_where=sa.text("is_published = false AND is_failed = false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("outbox_messages_not_published_idx")
