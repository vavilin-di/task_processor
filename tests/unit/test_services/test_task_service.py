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
