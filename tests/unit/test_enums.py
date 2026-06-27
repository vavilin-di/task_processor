import pytest

from src.enums import TaskPriority, TaskStatus


class TestTaskStatus:
    """Тесты для перечисления TaskStatus."""

    def test_members_count(self) -> None:
        assert len(TaskStatus) == 6  # noqa: S101, PLR2004

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (TaskStatus.NEW, "Новая задача"),
            (TaskStatus.PENDING, "Ожидает обработки"),
            (TaskStatus.IN_PROGRESS, "В процессе выполнения"),
            (TaskStatus.COMPLETED, "Завершена успешно"),
            (TaskStatus.FAILED, "Завершена с ошибкой"),
            (TaskStatus.CANCELLED, "Отменена"),
        ],
    )
    def test_values(self, status: TaskStatus, expected: str) -> None:
        assert status.value == expected  # noqa: S101

    def test_all_members_are_unique(self) -> None:
        values = [m.value for m in TaskStatus]
        assert len(values) == len(set(values))  # noqa: S101


class TestTaskPriority:
    """Тесты для перечисления TaskPriority."""

    def test_members_count(self) -> None:
        assert len(TaskPriority) == 3  # noqa: S101, PLR2004

    @pytest.mark.parametrize(
        ("priority", "expected"),
        [
            (TaskPriority.LOW, "Низкий"),
            (TaskPriority.MEDIUM, "Средний"),
            (TaskPriority.HIGH, "Высокий"),
        ],
    )
    def test_values(self, priority: TaskPriority, expected: str) -> None:
        assert priority.value == expected  # noqa: S101

    def test_all_members_are_unique(self) -> None:
        values = [m.value for m in TaskPriority]
        assert len(values) == len(set(values))  # noqa: S101

    def test_order(self) -> None:
        assert list(TaskPriority) == [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]  # noqa: S101
