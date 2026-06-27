__all__ = ["OutboxMessage"]

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import false
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import JSON, Boolean, String

from .base import Base


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    __table_args__ = (
        Index(
            "outbox_messages_not_published_idx",
            "created_at",
            postgresql_where=text("is_published = false AND is_failed = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aggregate_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", name="outbox_messages_aggregate_id_fkey", ondelete="CASCADE"), nullable=False
    )
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON(), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=false())
    is_failed: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    errors: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default_factory=list)
