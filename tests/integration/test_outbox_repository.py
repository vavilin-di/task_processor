from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.outbox_messages import OutboxMessage
from src.database.models.tasks import Task
from src.enums import TaskPriority, TaskStatus
from src.repositories.outbox_messages import OutboxMessageRepository
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session: AsyncSession) -> OutboxMessageRepository:
    return OutboxMessageRepository(OutboxMessage, session)


@pytest.fixture
def task_repo(session: AsyncSession) -> SQLAlchemyRepository[Task]:
    return SQLAlchemyRepository(Task, session)


def _task_kwargs(**overrides: Any) -> dict[str, Any]:
    """Базовые аргументы для создания задачи."""
    data: dict[str, Any] = {
        "name": "Test task",
        "description": "Test description",
        "priority": TaskPriority.MEDIUM,
        "status": TaskStatus.NEW,
        "payload": {},
    }
    data.update(overrides)
    return data


async def _create_task(task_repo: SQLAlchemyRepository[Task]) -> Task:
    """Создаёт задачу и возвращает её."""
    return await task_repo.create(**_task_kwargs())


async def _collect_messages(repo: OutboxMessageRepository, limit: int = 10) -> list[tuple[int, str, dict[str, Any]]]:
    """Собирает все сообщения из асинхронного генератора в список."""
    return [msg async for msg in repo.get_not_published_outbox_messages(limit=limit)]


class TestOutboxMessageRepository:
    """Integration-тесты для OutboxMessageRepository с реальной БД."""

    async def test_create_and_get_not_published(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task]
    ) -> None:
        task1 = await _create_task(task_repo)
        task2 = await _create_task(task_repo)
        await repo.create(routing_key="task.created", aggregate_id=task1.id, payload={"key": "value"})
        await repo.create(routing_key="task.updated", aggregate_id=task2.id, payload={"key2": "value2"})

        messages = await _collect_messages(repo)
        assert len(messages) == 2  # noqa: S101, PLR2004

    async def test_get_not_published_excludes_published(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task]
    ) -> None:
        task1 = await _create_task(task_repo)
        task2 = await _create_task(task_repo)
        msg1 = await repo.create(routing_key="task.created", aggregate_id=task1.id, payload={})
        await repo.create(routing_key="task.updated", aggregate_id=task2.id, payload={})

        await repo.mark_messages_as_published([msg1.id])

        messages = await _collect_messages(repo)
        assert len(messages) == 1  # noqa: S101

    async def test_get_not_published_excludes_failed(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task]
    ) -> None:
        task1 = await _create_task(task_repo)
        task2 = await _create_task(task_repo)
        msg1 = await repo.create(routing_key="task.created", aggregate_id=task1.id, payload={})
        await repo.create(routing_key="task.updated", aggregate_id=task2.id, payload={})

        # Добавляем 5 ошибок, чтобы is_failed стал True
        for i in range(5):
            await repo.add_error(task_id=msg1.id, error=f"Error {i}")

        messages = await _collect_messages(repo)
        assert len(messages) == 1  # noqa: S101

    async def test_mark_messages_as_published(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task], session: AsyncSession
    ) -> None:
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})

        await repo.mark_messages_as_published([msg.id])

        stmt = select(OutboxMessage).where(OutboxMessage.id == msg.id)
        result = await session.execute(stmt)
        message = result.scalar_one()
        assert message.is_published is True  # noqa: S101

    async def test_add_error_increments_errors(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task], session: AsyncSession
    ) -> None:
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})

        await repo.add_error(task_id=msg.id, error="First error")
        await repo.add_error(task_id=msg.id, error="Second error")

        stmt = select(OutboxMessage).where(OutboxMessage.id == msg.id)
        result = await session.execute(stmt)
        message = result.scalar_one()
        assert len(message.errors) == 2  # noqa: S101, PLR2004
        assert message.errors == ["First error", "Second error"]  # noqa: S101

    async def test_add_error_marks_failed_on_threshold(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task], session: AsyncSession
    ) -> None:
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})

        for i in range(5):
            await repo.add_error(task_id=msg.id, error=f"Error {i}")

        stmt = select(OutboxMessage).where(OutboxMessage.id == msg.id)
        result = await session.execute(stmt)
        message = result.scalar_one()
        assert message.is_failed is True  # noqa: S101

    async def test_delete_published_older_than__deletes_expired(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task], session: AsyncSession
    ) -> None:
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})

        await repo.mark_messages_as_published([msg.id])

        old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=48)
        await repo.update(msg.id, created_at=old_date)

        deleted = await repo.delete_published_older_than(ttl_hours=24, batch_size=100)

        assert deleted == 1  # noqa: S101

        stmt = select(OutboxMessage).where(OutboxMessage.id == msg.id)
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is None  # noqa: S101

    async def test_delete_published_older_than__skips_recent(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task]
    ) -> None:
        """Свежие сообщения не удаляются."""
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})
        await repo.mark_messages_as_published([msg.id])

        deleted = await repo.delete_published_older_than(ttl_hours=24, batch_size=100)

        assert deleted == 0  # noqa: S101

    async def test_delete_published_older_than__skips_unpublished(
        self, repo: OutboxMessageRepository, task_repo: SQLAlchemyRepository[Task], session: AsyncSession
    ) -> None:
        """Неопубликованные сообщения не удаляются, даже если старые."""
        task = await _create_task(task_repo)
        msg = await repo.create(routing_key="task.created", aggregate_id=task.id, payload={})

        old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=48)
        await repo.update(msg.id, created_at=old_date)

        deleted = await repo.delete_published_older_than(ttl_hours=24, batch_size=100)

        assert deleted == 0  # noqa: S101

        stmt = select(OutboxMessage).where(OutboxMessage.id == msg.id)
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is not None  # noqa: S101
