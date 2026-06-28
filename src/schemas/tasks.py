__all__ = ["TaskCreate", "Task"]

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic.config import ConfigDict

from src.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class Task(BaseModel):
    id: int
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any] | None
    errors: list[str] | None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TaskFilter(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    started_at_from: datetime | None = None
    started_at_to: datetime | None = None
    finished_at_from: datetime | None = None
    finished_at_to: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
