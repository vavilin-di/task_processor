__all__ = ["Task"]

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import true
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import JSON, Boolean, DateTime, String

from src.enums import TaskPriority, TaskStatus

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    description: Mapped[str] = mapped_column(String(), nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(String(), nullable=False, default=TaskPriority.MEDIUM.value)
    status: Mapped[TaskStatus] = mapped_column(String(), nullable=False, default=TaskStatus.NEW.value)
    payload: Mapped[dict] = mapped_column(JSON(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, server_default=func.now())
    started_at: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(), nullable=True)
    result: Mapped[dict] = mapped_column(JSON(), nullable=True)
    errors: Mapped[list[str] | None] = mapped_column(JSON(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=true())
