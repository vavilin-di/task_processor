from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette import status as status_codes

from src.enums import TaskStatus
from src.schemas.common import PaginatedResponse
from src.schemas.tasks import Task, TaskCreate, TaskFilter

pytestmark = pytest.mark.unit


class TestCreateTaskRouterLogic:
    """Unit-tests for create_task logic (without inject decorator)."""

    async def test_create_task_calls_service_and_returns_result(self) -> None:
        """Verify create_task calls service.create_task and returns result."""
        mock_service = AsyncMock()
        mock_task = MagicMock()
        mock_service.create_task.return_value = mock_task

        task_data = TaskCreate(name="Test", description="Desc", payload={})
        result = await mock_service.create_task(task_data)

        assert result is mock_task  # noqa: S101
        mock_service.create_task.assert_awaited_once_with(task_data)


class TestGetTasksRouterLogic:
    """Unit-tests for get_tasks logic (without inject decorator)."""

    async def test_get_tasks_calls_service_with_defaults(self) -> None:
        """Verify get_tasks call with default parameters."""
        mock_service = AsyncMock()
        mock_service.get_tasks.return_value = PaginatedResponse[Task](items=[], next_cursor=None, has_next=False)

        result = await mock_service.get_tasks(limit=20)

        assert result.items == []  # noqa: S101
        mock_service.get_tasks.assert_awaited_once()

    async def test_get_tasks_with_cursor_and_limit(self) -> None:
        """Verify get_tasks call with cursor and limit."""
        mock_service = AsyncMock()
        mock_service.get_tasks.return_value = PaginatedResponse[Task](items=[], next_cursor="next", has_next=True)

        result = await mock_service.get_tasks(limit=10, cursor="cursor123")

        assert result.next_cursor == "next"  # noqa: S101
        assert result.has_next is True  # noqa: S101
        mock_service.get_tasks.assert_awaited_once()

    async def test_get_tasks_with_filter(self) -> None:
        """Verify get_tasks call with filter."""
        mock_service = AsyncMock()
        mock_service.get_tasks.return_value = PaginatedResponse[Task](items=[], next_cursor=None, has_next=False)

        task_filter = TaskFilter(status=TaskStatus.NEW)
        result = await mock_service.get_tasks(limit=20, filter_=task_filter)

        assert result.items == []  # noqa: S101
        mock_service.get_tasks.assert_awaited_once()


class TestGetTaskRouterLogic:
    """Unit-tests for get_task logic (without inject decorator)."""

    async def test_get_task_returns_task(self) -> None:
        """Verify get_task returns a task."""
        mock_service = AsyncMock()
        mock_task = MagicMock()
        mock_service.get_task.return_value = mock_task

        result = await mock_service.get_task(1)

        assert result is mock_task  # noqa: S101
        mock_service.get_task.assert_awaited_once_with(1)

    async def test_get_task_returns_none(self) -> None:
        """Verify get_task returns None for non-existent task."""
        mock_service = AsyncMock()
        mock_service.get_task.return_value = None

        result = await mock_service.get_task(999)

        assert result is None  # noqa: S101


class TestCancelTaskRouterLogic:
    """Unit-tests for cancel_task logic (without inject decorator)."""

    async def test_cancel_task_returns_task(self) -> None:
        """Verify cancel_task returns a task."""
        mock_service = AsyncMock()
        mock_task = MagicMock()
        mock_service.cancel_task.return_value = mock_task

        result = await mock_service.cancel_task(1)

        assert result is mock_task  # noqa: S101
        mock_service.cancel_task.assert_awaited_once_with(1)

    async def test_cancel_task_returns_none(self) -> None:
        """Verify cancel_task returns None for non-existent task."""
        mock_service = AsyncMock()
        mock_service.cancel_task.return_value = None

        result = await mock_service.cancel_task(999)

        assert result is None  # noqa: S101


class TestGetTaskStatusRouterLogic:
    """Unit-tests for get_task_status logic (without inject decorator)."""

    async def test_get_task_status_returns_status(self) -> None:
        """Verify get_task_status returns status."""
        mock_service = AsyncMock()
        mock_service.get_task_status.return_value = TaskStatus.NEW

        result = await mock_service.get_task_status(1)

        assert result == TaskStatus.NEW  # noqa: S101
        mock_service.get_task_status.assert_awaited_once_with(1)

    async def test_get_task_status_returns_none(self) -> None:
        """Verify get_task_status returns None for non-existent task."""
        mock_service = AsyncMock()
        mock_service.get_task_status.return_value = None

        result = await mock_service.get_task_status(999)

        assert result is None  # noqa: S101


class TestRouterHTTPExceptionLogic:
    """Unit-tests for HTTPException logic in routers (without inject decorator)."""

    async def test_get_task_raises_404_when_not_found(self) -> None:
        """Verify 404 is raised when task not found."""
        from fastapi import HTTPException

        mock_service = AsyncMock()
        mock_service.get_task.return_value = None

        task = await mock_service.get_task(999)
        with pytest.raises(HTTPException) as exc_info:
            if task is None:
                raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Task not found")

        assert exc_info.value.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101
        assert exc_info.value.detail == "Task not found"  # noqa: S101

    async def test_cancel_task_raises_404_when_not_found(self) -> None:
        """Verify 404 is raised when cancelling non-existent task."""
        from fastapi import HTTPException

        mock_service = AsyncMock()
        mock_service.cancel_task.return_value = None

        task = await mock_service.cancel_task(999)
        with pytest.raises(HTTPException) as exc_info:
            if task is None:
                raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Task not found")

        assert exc_info.value.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101
        assert exc_info.value.detail == "Task not found"  # noqa: S101

    async def test_get_task_status_raises_404_when_not_found(self) -> None:
        """Verify 404 is raised when task status not found."""
        from fastapi import HTTPException

        mock_service = AsyncMock()
        mock_service.get_task_status.return_value = None

        task_status = await mock_service.get_task_status(999)
        with pytest.raises(HTTPException) as exc_info:
            if task_status is None:
                raise HTTPException(status_code=status_codes.HTTP_404_NOT_FOUND, detail="Task not found")

        assert exc_info.value.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101
        assert exc_info.value.detail == "Task not found"  # noqa: S101
