from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.models.tasks import Task
from src.enums import TaskStatus
from src.repositories.tasks import TaskRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def task_repo(mock_session: AsyncMock) -> TaskRepository:
    with patch("src.repositories.tasks.SoftDeleteSQLAlchemyRepository.__init__", return_value=None):
        repo = TaskRepository.__new__(TaskRepository)
        repo._session = mock_session
        repo._model = Task
        return repo


class TestTaskRepository:
    """Unit-тесты для TaskRepository с замокированным SoftDeleteSQLAlchemyRepository."""

    async def test_cancel_task_calls_update_with_cancelled(self, task_repo: TaskRepository) -> None:
        task_repo.update = AsyncMock(return_value=MagicMock())  # type: ignore[method-assign]
        result = await task_repo.cancel_task(record_id=1)
        task_repo.update.assert_awaited_once_with(record_id=1, status=TaskStatus.CANCELLED)
        assert result is not None  # noqa: S101

    async def test_cancel_task_returns_none_when_not_found(self, task_repo: TaskRepository) -> None:
        task_repo.update = AsyncMock(return_value=None)  # type: ignore[method-assign]
        result = await task_repo.cancel_task(record_id=999)
        assert result is None  # noqa: S101

    async def test_get_task_status_returns_status(self, task_repo: TaskRepository) -> None:
        task_repo.get_value = AsyncMock(return_value=TaskStatus.NEW)  # type: ignore[method-assign]
        status = await task_repo.get_task_status(record_id=1)
        assert status is TaskStatus.NEW  # noqa: S101
        task_repo.get_value.assert_awaited_once_with(1, task_repo._model.status)

    async def test_get_task_status_returns_none_for_missing(self, task_repo: TaskRepository) -> None:
        task_repo.get_value = AsyncMock(return_value=None)  # type: ignore[method-assign]
        status = await task_repo.get_task_status(record_id=999)
        assert status is None  # noqa: S101
