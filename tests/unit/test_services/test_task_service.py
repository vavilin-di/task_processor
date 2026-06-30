from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.enums import TaskStatus
from src.services.tasks import TaskService

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    begin_context = AsyncMock()
    begin_context.__aenter__ = AsyncMock()
    begin_context.__aexit__ = AsyncMock()
    session.begin = MagicMock(return_value=begin_context)
    return session


@pytest.fixture
def mock_task_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_outbox_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(
    mock_session: MagicMock,
    mock_task_repo: AsyncMock,
    mock_outbox_repo: AsyncMock,
) -> TaskService:
    return TaskService(
        task_repository=mock_task_repo,
        outbox_repository=mock_outbox_repo,
        session=mock_session,
    )


class TestTaskServiceProcessTask:
    """Unit-тесты для TaskService.process_task."""

    async def test_process_task_updates_status_to_in_progress_then_completed(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """process_task переводит задачу из NEW в IN_PROGRESS, затем в COMPLETED."""
        mock_task = MagicMock()
        mock_task_repo.update.return_value = mock_task

        with patch("src.services.tasks.asyncio.sleep", AsyncMock()):
            result = await service.process_task(task_id=1)

        assert result is mock_task  # noqa: S101
        # Первый вызов update — IN_PROGRESS
        first_call = mock_task_repo.update.await_args_list[0]
        assert first_call.kwargs["record_id"] == 1  # noqa: S101
        assert first_call.kwargs["status"] == TaskStatus.IN_PROGRESS  # noqa: S101
        assert first_call.kwargs["started_at"] is not None  # noqa: S101

        # Второй вызов update — COMPLETED
        second_call = mock_task_repo.update.await_args_list[1]
        assert second_call.kwargs["record_id"] == 1  # noqa: S101
        assert second_call.kwargs["status"] == TaskStatus.COMPLETED  # noqa: S101
        assert second_call.kwargs["finished_at"] is not None  # noqa: S101
        assert second_call.kwargs["result"] == {"message": "Задача успешно обработана"}  # noqa: S101

    async def test_process_task_returns_none_when_task_not_found(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """Если задача не найдена, process_task возвращает None."""
        mock_task_repo.update.return_value = None

        result = await service.process_task(task_id=999)

        assert result is None  # noqa: S101
        assert mock_task_repo.update.await_count == 1  # noqa: S101


class TestTaskServiceFailTask:
    """Unit-тесты для TaskService.fail_task."""

    async def test_fail_task_updates_status_to_failed(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """fail_task переводит задачу в FAILED с ошибками."""
        mock_task = MagicMock()
        mock_task_repo.update.return_value = mock_task

        result = await service.fail_task(task_id=1, errors=["Test error"])

        assert result is mock_task  # noqa: S101
        mock_task_repo.update.assert_awaited_once_with(
            record_id=1,
            status=TaskStatus.FAILED,
            finished_at=mock_task_repo.update.await_args.kwargs["finished_at"],
            errors=["Test error"],
        )

    async def test_fail_task_uses_default_errors(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """Если errors не переданы, используются ошибки по умолчанию."""
        mock_task = MagicMock()
        mock_task_repo.update.return_value = mock_task

        result = await service.fail_task(task_id=1)

        assert result is mock_task  # noqa: S101
        assert mock_task_repo.update.await_args.kwargs["errors"] == ["Внутренняя ошибка обработчика"]  # noqa: S101


class TestTaskServiceCreateTask:
    """Unit-тесты для TaskService.create_task."""

    async def test_create_task_creates_task_and_outbox_message(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
        mock_outbox_repo: AsyncMock,
    ) -> None:
        """create_task создаёт задачу и outbox-сообщение."""
        from src.schemas.tasks import TaskCreate

        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.payload = {"key": "value"}
        mock_task_repo.create.return_value = mock_task

        task_create = TaskCreate(name="Test", description="Desc", payload={"key": "value"})
        result = await service.create_task(task_create)

        assert result is mock_task  # noqa: S101
        mock_task_repo.create.assert_awaited_once_with(**task_create.model_dump())
        mock_outbox_repo.create.assert_awaited_once()


class TestTaskServiceGetTasks:
    """Unit-тесты для TaskService.get_tasks."""

    async def test_get_tasks_without_filter(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_tasks без фильтра."""
        from src.schemas.tasks import Task as TaskSchema

        mock_task = MagicMock(spec=["id", "name", "description", "priority", "status", "created_at"])
        mock_task.id = 1
        mock_task.name = "Test"
        mock_task.description = "Desc"
        mock_task.priority = "Средний"
        mock_task.status = "Новая задача"
        mock_task.created_at = "2024-01-01T00:00:00"
        mock_task.started_at = None
        mock_task.finished_at = None
        mock_task.result = None
        mock_task.errors = None
        mock_task.is_active = True
        mock_task_repo.get_all.return_value = ([mock_task], "next_cursor", True)

        with patch("src.services.tasks.task_list_adapter.validate_python") as mock_validate:
            mock_validate.return_value = [TaskSchema.model_validate(mock_task)]
            result = await service.get_tasks(limit=20)

        mock_task_repo.get_all.assert_awaited_once_with(None, 20, None)
        assert len(result.items) == 1  # noqa: S101
        assert result.next_cursor == "next_cursor"  # noqa: S101
        assert result.has_next is True  # noqa: S101

    async def test_get_tasks_with_filter(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_tasks с фильтром."""
        from src.schemas.tasks import Task as TaskSchema
        from src.schemas.tasks import TaskFilter

        mock_task = MagicMock(spec=["id", "name", "description", "priority", "status", "created_at"])
        mock_task.id = 1
        mock_task.name = "Test"
        mock_task.description = "Desc"
        mock_task.priority = "Средний"
        mock_task.status = "Новая задача"
        mock_task.created_at = "2024-01-01T00:00:00"
        mock_task.started_at = None
        mock_task.finished_at = None
        mock_task.result = None
        mock_task.errors = None
        mock_task.is_active = True
        mock_task_repo.get_all.return_value = ([mock_task], None, False)

        task_filter = TaskFilter(status=TaskStatus.NEW)
        with patch("src.services.tasks.task_list_adapter.validate_python") as mock_validate:
            mock_validate.return_value = [TaskSchema.model_validate(mock_task)]
            result = await service.get_tasks(limit=10, cursor="cursor123", filter_=task_filter)

        mock_task_repo.get_all.assert_awaited_once_with("cursor123", 10, task_filter.model_dump(exclude_none=True))
        assert len(result.items) == 1  # noqa: S101, PLR2004
        assert result.next_cursor is None  # noqa: S101
        assert result.has_next is False  # noqa: S101

    async def test_get_tasks_with_empty_result(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_tasks возвращает пустой список."""
        mock_task_repo.get_all.return_value = ([], None, False)

        with patch("src.services.tasks.task_list_adapter.validate_python") as mock_validate:
            mock_validate.return_value = []
            result = await service.get_tasks(limit=20)

        assert result.items == []  # noqa: S101
        assert result.next_cursor is None  # noqa: S101
        assert result.has_next is False  # noqa: S101


class TestTaskServiceGetTask:
    """Unit-тесты для TaskService.get_task."""

    async def test_get_task_returns_task(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_task возвращает задачу."""
        mock_task = MagicMock()
        mock_task_repo.get.return_value = mock_task

        result = await service.get_task(task_id=1)

        assert result is mock_task  # noqa: S101
        mock_task_repo.get.assert_awaited_once_with(1)

    async def test_get_task_returns_none(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_task возвращает None для несуществующей задачи."""
        mock_task_repo.get.return_value = None

        result = await service.get_task(task_id=999)

        assert result is None  # noqa: S101
        mock_task_repo.get.assert_awaited_once_with(999)


class TestTaskServiceCancelTask:
    """Unit-тесты для TaskService.cancel_task."""

    async def test_cancel_task_cancels(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """cancel_task отменяет задачу."""
        mock_task = MagicMock()
        mock_task_repo.cancel_task.return_value = mock_task

        result = await service.cancel_task(task_id=1)

        assert result is mock_task  # noqa: S101
        mock_task_repo.cancel_task.assert_awaited_once_with(1)

    async def test_cancel_task_returns_none(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """cancel_task возвращает None для несуществующей задачи."""
        mock_task_repo.cancel_task.return_value = None

        result = await service.cancel_task(task_id=999)

        assert result is None  # noqa: S101
        mock_task_repo.cancel_task.assert_awaited_once_with(999)


class TestTaskServiceGetTaskStatus:
    """Unit-тесты для TaskService.get_task_status."""

    async def test_get_task_status_returns_status(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_task_status возвращает статус задачи."""
        mock_task_repo.get_task_status.return_value = TaskStatus.NEW

        result = await service.get_task_status(task_id=1)

        assert result == TaskStatus.NEW  # noqa: S101
        mock_task_repo.get_task_status.assert_awaited_once_with(1)

    async def test_get_task_status_returns_none(
        self,
        service: TaskService,
        mock_task_repo: AsyncMock,
    ) -> None:
        """get_task_status возвращает None для несуществующей задачи."""
        mock_task_repo.get_task_status.return_value = None

        result = await service.get_task_status(task_id=999)

        assert result is None  # noqa: S101
        mock_task_repo.get_task_status.assert_awaited_once_with(999)
