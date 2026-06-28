from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.tasks import Task
from src.enums import TaskPriority, TaskStatus
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session: AsyncSession) -> SQLAlchemyRepository[Task]:
    return SQLAlchemyRepository(Task, session)


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


class TestSQLAlchemyRepository:
    """Integration-тесты для SQLAlchemyRepository на модели Task."""

    async def test_create_and_get(self, repo: SQLAlchemyRepository[Task]) -> None:
        task = await repo.create(**_task_kwargs())
        assert task.id is not None  # noqa: S101
        assert task.name == "Test task"  # noqa: S101

        fetched = await repo.get(task.id)
        assert fetched is not None  # noqa: S101
        assert fetched.id == task.id  # noqa: S101

    async def test_get_returns_none_for_deleted(self, repo: SQLAlchemyRepository[Task]) -> None:
        task = await repo.create(**_task_kwargs(name="To delete"))
        await repo.delete(task.id)

        fetched = await repo.get(task.id)
        assert fetched is None  # noqa: S101

    async def test_get_all_with_cursor_pagination(self, repo: SQLAlchemyRepository[Task]) -> None:
        for i in range(5):
            await repo.create(**_task_kwargs(name=f"Task {i}", description=f"Desc {i}"))

        items, cursor, _ = await repo.get_all(cursor=None, limit=3, filters=None)
        assert len(items) == 3  # noqa: S101, PLR2004
        assert cursor is not None  # noqa: S101

    async def test_get_all_with_filters(self, repo: SQLAlchemyRepository[Task]) -> None:
        await repo.create(**_task_kwargs(name="High priority", priority=TaskPriority.HIGH))
        await repo.create(**_task_kwargs(name="Low priority", priority=TaskPriority.LOW))

        items, _, _ = await repo.get_all(cursor=None, limit=10, filters={"priority": TaskPriority.HIGH})
        assert len(items) == 1  # noqa: S101
        assert items[0].name == "High priority"  # noqa: S101

    async def test_update(self, repo: SQLAlchemyRepository[Task]) -> None:
        task = await repo.create(**_task_kwargs(name="Original"))
        updated = await repo.update(task.id, name="Updated")
        assert updated is not None  # noqa: S101
        assert updated.name == "Updated"  # noqa: S101

    async def test_update_returns_none_for_missing(self, repo: SQLAlchemyRepository[Task]) -> None:
        result = await repo.update(999, name="Nope")
        assert result is None  # noqa: S101

    async def test_delete_removes_record(self, repo: SQLAlchemyRepository[Task], session: AsyncSession) -> None:
        task = await repo.create(**_task_kwargs(name="To delete"))
        await repo.delete(task.id)

        stmt = select(Task).where(Task.id == task.id)
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is None  # noqa: S101
