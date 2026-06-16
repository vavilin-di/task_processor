__all__ = ["TaskCreate", "Task"]

from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict

from src.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    name: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.NEW
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None = None
    result: dict
    errors: list[str] | None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class Task(BaseModel):
    id: int
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: datetime
    finished_at: datetime | None
    result: dict
    errors: list[str] | None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class TaskFilter(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    is_active: bool | None = None
