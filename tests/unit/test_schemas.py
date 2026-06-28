from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from src.enums import TaskPriority, TaskStatus
from src.schemas.common import PaginatedResponse
from src.schemas.dlq_messages import DLQMessage, DLQMessageCreate
from src.schemas.outbox_messages import OutboxMessage, OutboxMessageCreate
from src.schemas.tasks import Task, TaskCreate, TaskFilter

ROUTING_KEY = "task.created"


def _make_task_create_data(**overrides: Any) -> dict[str, Any]:
    """Базовые данные для создания задачи."""
    data: dict[str, Any] = {
        "name": "Test task",
        "description": "Test description",
        "priority": TaskPriority.MEDIUM,
        "payload": {"key": "value"},
    }
    data.update(overrides)
    return data


class TestTaskCreate:
    """Тесты для схемы создания задачи."""

    def test_valid_data(self) -> None:
        data = _make_task_create_data()
        task = TaskCreate(**data)
        assert task.name == "Test task"  # noqa: S101
        assert task.priority == TaskPriority.MEDIUM  # noqa: S101
        assert task.payload == {"key": "value"}  # noqa: S101

    def test_default_priority(self) -> None:
        task = TaskCreate(name="Default test", description="Desc", payload={})
        assert task.priority == TaskPriority.MEDIUM  # noqa: S101

    def test_missing_required_field_raises_error(self) -> None:
        with pytest.raises(ValidationError):
            TaskCreate()  # type: ignore[call-arg]

    def test_invalid_priority_raises_error(self) -> None:
        data = _make_task_create_data(priority="INVALID")
        with pytest.raises(ValidationError):
            TaskCreate(**data)


class TestTask:
    """Тесты для схемы задачи (с id)."""

    def test_from_attributes(self) -> None:
        """Проверка from_attributes=True — создание из ORM-подобного объекта."""
        data: dict[str, Any] = {
            "id": 1,
            "name": "Test task",
            "description": "Test description",
            "priority": TaskPriority.MEDIUM,
            "status": TaskStatus.NEW,
            "created_at": datetime.now(UTC),
            "started_at": datetime.now(UTC),
            "finished_at": None,
            "result": {},
            "errors": None,
            "is_active": True,
        }
        task = Task.model_validate(data)
        assert task.id == 1  # noqa: S101
        assert task.name == "Test task"  # noqa: S101

    def test_with_all_fields(self) -> None:
        data: dict[str, Any] = {
            "id": 42,
            "name": "Full task",
            "description": "Desc",
            "priority": TaskPriority.HIGH,
            "status": TaskStatus.IN_PROGRESS,
            "created_at": datetime.now(UTC),
            "started_at": datetime.now(UTC),
            "finished_at": None,
            "result": {"key": "value"},
            "errors": ["error1"],
            "is_active": True,
        }
        task = Task.model_validate(data)
        assert task.id == data["id"]  # noqa: S101
        assert task.errors == ["error1"]  # noqa: S101


class TestTaskFilter:
    """Тесты для схемы фильтрации задач."""

    def test_all_none(self) -> None:
        filter_ = TaskFilter()
        assert filter_.model_dump(exclude_none=True) == {}  # noqa: S101

    def test_with_some_fields(self) -> None:
        filter_ = TaskFilter(name="test", status=TaskStatus.NEW)
        dumped = filter_.model_dump(exclude_none=True)
        assert dumped == {"name": "test", "status": TaskStatus.NEW}  # noqa: S101

    def test_with_all_fields(self) -> None:
        filter_ = TaskFilter(
            name="test",
            description="desc",
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            created_at_from=datetime.now(UTC),
            created_at_to=datetime.now(UTC),
            started_at_from=datetime.now(UTC),
            started_at_to=datetime.now(UTC),
            finished_at_from=datetime.now(UTC),
            finished_at_to=datetime.now(UTC),
        )
        dumped = filter_.model_dump(exclude_none=True)
        assert "name" in dumped  # noqa: S101
        assert "description" in dumped  # noqa: S101
        assert "priority" in dumped  # noqa: S101
        assert "status" in dumped  # noqa: S101
        assert "created_at_from" in dumped  # noqa: S101
        assert "created_at_to" in dumped  # noqa: S101
        assert "started_at_from" in dumped  # noqa: S101
        assert "started_at_to" in dumped  # noqa: S101
        assert "finished_at_from" in dumped  # noqa: S101
        assert "finished_at_to" in dumped  # noqa: S101


class TestPaginatedResponse:
    """Тесты для схемы пагинированного ответа."""

    def test_with_string_items(self) -> None:
        response = PaginatedResponse[str](items=["a", "b"], next_cursor="cursor123", has_next=True)
        assert response.items == ["a", "b"]  # noqa: S101
        assert response.next_cursor == "cursor123"  # noqa: S101
        assert response.has_next is True  # noqa: S101

    def test_with_dict_items(self) -> None:
        items: list[dict[str, int | str]] = [{"id": 1, "name": "test"}]
        response = PaginatedResponse[dict[str, int | str]](items=items, next_cursor=None, has_next=False)
        assert response.items == items  # noqa: S101
        assert response.next_cursor is None  # noqa: S101
        assert response.has_next is False  # noqa: S101

    def test_empty_items(self) -> None:
        response = PaginatedResponse[Any](items=[], next_cursor=None, has_next=False)
        assert response.items == []  # noqa: S101


class TestOutboxMessageCreate:
    """Тесты для схемы создания outbox-сообщения."""

    def test_valid_data(self) -> None:
        message = OutboxMessageCreate(routing_key=ROUTING_KEY, aggregate_id=1, payload={"key": "value"})
        assert message.aggregate_id == 1  # noqa: S101
        assert message.payload == {"key": "value"}  # noqa: S101

    def test_missing_aggregate_id_raises_error(self) -> None:
        with pytest.raises(ValidationError):
            OutboxMessageCreate(payload={})  # type: ignore[call-arg]


class TestOutboxMessage:
    """Тесты для схемы OutboxMessage."""

    def test_valid_data(self) -> None:
        message = OutboxMessage(id=1, routing_key=ROUTING_KEY, payload={"key": "value"})
        assert message.id == 1  # noqa: S101
        assert message.routing_key == ROUTING_KEY  # noqa: S101
        assert message.payload == {"key": "value"}  # noqa: S101


class TestDLQMessageCreate:
    """Тесты для схемы создания DLQ-сообщения."""

    def test_valid_data(self) -> None:
        message = DLQMessageCreate(
            original_routing_key="task.created",
            original_payload={"key": "value"},
            error_type="TestError",
            error_message="Something went wrong",
            retry_count=0,
            x_death=None,
        )
        assert message.original_routing_key == "task.created"  # noqa: S101
        assert message.retry_count == 0  # noqa: S101
        assert message.x_death is None  # noqa: S101

    def test_with_x_death(self) -> None:
        x_death: list[dict[str, Any]] = [{"count": 1, "reason": "rejected"}]
        message = DLQMessageCreate(
            original_routing_key="task.created",
            original_payload={},
            error_type="Error",
            error_message="Msg",
            retry_count=1,
            x_death=x_death,
        )
        assert message.x_death == x_death  # noqa: S101


class TestDLQMessage:
    """Тесты для схемы DLQMessage."""

    def test_valid_data(self) -> None:
        now = datetime.now(UTC)
        message = DLQMessage(
            id=1,
            original_routing_key="task.created",
            original_payload={"key": "value"},
            error_type="TestError",
            error_message="Something went wrong",
            retry_count=0,
            x_death=None,
            created_at=now,
        )
        assert message.id == 1  # noqa: S101
        assert message.created_at == now  # noqa: S101
