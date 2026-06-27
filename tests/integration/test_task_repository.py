from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.tasks import Task
from src.enums import TaskPriority, TaskStatus
from src.repositories.tasks import TaskRepository


@pytest.fixture
def repo(session: AsyncSession) -> TaskRepository:
    return TaskRepository(Task, session)


def _task_kwargs(**overrides: Any) -> dict[str, Any]:
    """Базовые аргументы для создания задачи через репозиторий."""
    data: dict[str, Any] = {
        "name": "Test task",
        "description": "Test description",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.NEW,
        "payload": {},
    }
    data.update(overrides)
    return data


class TestTaskRepository:
    """Integration-тесты для TaskRepository с реальной БД."""

    async def test_cancel_task(self, repo: TaskRepository) -> None:
        task = await repo.create(**_task_kwargs(name="To cancel"))
        cancelled = await repo.cancel_task(record_id=task.id)
        assert cancelled is not None  # noqa: S101
        assert cancelled.status == TaskStatus.CANCELLED  # noqa: S101

    async def test_cancel_task_returns_none_for_missing(self, repo: TaskRepository) -> None:
        result = await repo.cancel_task(record_id=999)
        assert result is None  # noqa: S101

    async def test_get_task_status(self, repo: TaskRepository) -> None:
        task = await repo.create(**_task_kwargs(name="Status check"))
        status = await repo.get_task_status(record_id=task.id)
        assert status == TaskStatus.NEW  # noqa: S101

    async def test_get_task_status_returns_none_for_missing(self, repo: TaskRepository) -> None:
        status = await repo.get_task_status(record_id=999)
        assert status is None  # noqa: S101

    async def test_soft_delete(self, repo: TaskRepository, session: AsyncSession) -> None:
        task = await repo.create(**_task_kwargs(name="To soft delete"))
        await repo.delete(task.id)

        stmt = select(Task).where(Task.id == task.id)
        result = await session.execute(stmt)
        deleted_task = result.scalar_one()
        assert deleted_task.is_active is False  # noqa: S101

    async def test_get_returns_none_for_soft_deleted(self, repo: TaskRepository) -> None:
        task = await repo.create(**_task_kwargs(name="To hide"))
        await repo.delete(task.id)

        fetched = await repo.get(task.id)
        assert fetched is None  # noqa: S101
