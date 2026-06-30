import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.outbox_messages import OutboxMessage
from src.database.models.tasks import Task
from src.enums import TaskPriority, TaskStatus
from src.repositories.outbox_messages import OutboxMessageRepository
from src.repositories.tasks import TaskRepository
from src.schemas.tasks import TaskCreate
from src.services.tasks import TaskService

pytestmark = pytest.mark.integration


@pytest.fixture
def task_repo(session: AsyncSession) -> TaskRepository:
    return TaskRepository(Task, session)


@pytest.fixture
def outbox_repo(session: AsyncSession) -> OutboxMessageRepository:
    return OutboxMessageRepository(OutboxMessage, session)


@pytest.fixture
def service(session: AsyncSession, task_repo: TaskRepository, outbox_repo: OutboxMessageRepository) -> TaskService:
    return TaskService(task_repository=task_repo, outbox_repository=outbox_repo, session=session)


class TestTaskServiceProcessTaskIntegration:
    """Integration-тесты для TaskService.process_task с реальной БД."""

    async def test_process_task_updates_status_to_completed(self, service: TaskService, session: AsyncSession) -> None:
        """process_task переводит задачу из NEW в IN_PROGRESS, затем в COMPLETED."""
        task = await service.create_task(
            TaskCreate(
                name="Integration test task",
                description="Test description",
                priority=TaskPriority.MEDIUM,
                payload={"key": "value"},
            )
        )
        task_id = task.id

        result = await service.process_task(task_id)

        assert result is not None  # noqa: S101
        assert result.status == TaskStatus.COMPLETED  # noqa: S101
        assert result.started_at is not None  # noqa: S101
        assert result.finished_at is not None  # noqa: S101
        assert result.result == {"message": "Задача успешно обработана"}  # noqa: S101

    async def test_process_task_returns_none_for_missing(self, service: TaskService) -> None:
        """process_task возвращает None для несуществующей задачи."""
        result = await service.process_task(task_id=999)
        assert result is None  # noqa: S101

    async def test_fail_task_updates_status_to_failed(self, service: TaskService, session: AsyncSession) -> None:
        """fail_task переводит задачу в FAILED."""
        task = await service.create_task(
            TaskCreate(
                name="Fail test task",
                description="Test description",
                priority=TaskPriority.LOW,
                payload={},
            )
        )
        task_id = task.id

        result = await service.fail_task(task_id, errors=["Test error"])

        assert result is not None  # noqa: S101
        assert result.status == TaskStatus.FAILED  # noqa: S101
        assert result.finished_at is not None  # noqa: S101
        assert result.errors == ["Test error"]  # noqa: S101

    async def test_fail_task_returns_none_for_missing(self, service: TaskService) -> None:
        """fail_task возвращает None для несуществующей задачи."""
        result = await service.fail_task(task_id=999)
        assert result is None  # noqa: S101
