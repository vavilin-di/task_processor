__all__ = ["DLQMessage"]

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import true
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import JSON, Boolean, String

from .base import Base


class DLQMessage(Base):
    __tablename__ = "dlq_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_routing_key: Mapped[str] = mapped_column(String(255), nullable=False)
    original_payload: Mapped[dict] = mapped_column(JSON(), nullable=False)
    error_type: Mapped[str] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text(), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    x_death: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=true())
