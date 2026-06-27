"""add_dlq_table

Revision ID: c97449149006
Revises: f65ad40b16f7
Create Date: 2026-06-27 23:35:32.490883

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c97449149006"
down_revision: str | Sequence[str] | None = "6188ca6a09bb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "dlq_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_routing_key", sa.String(length=255), nullable=False),
        sa.Column("original_payload", sa.JSON(), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("x_death", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("dlq_messages")
