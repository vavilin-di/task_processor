__all__ = ["OutboxMessage"]

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import false, true
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import JSON, Boolean, String

from .base import Base


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    aggregate_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON(), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=false())
    is_failed: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=true())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    errors: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default="[]")
