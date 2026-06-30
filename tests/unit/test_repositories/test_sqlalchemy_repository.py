from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.database.models.tasks import Task
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository

pytestmark = pytest.mark.unit


class TestSQLAlchemyRepositoryUnit:
    """Unit-тесты для SQLAlchemyRepository (логика фильтрации)."""

    @pytest.fixture
    def repo(self) -> SQLAlchemyRepository[Task]:
        with patch.object(SQLAlchemyRepository, "__init__", return_value=None):
            repo = SQLAlchemyRepository.__new__(SQLAlchemyRepository)
            repo._model = Task
            return repo

    def test_get_filtered_statement_with_eq_filter(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Фильтр по точному совпадению поля."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"priority": "HIGH"})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.priority" in compiled  # noqa: S101
        assert "HIGH" in compiled  # noqa: S101

    def test_get_filtered_statement_with_from_filter(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Фильтр с суффиксом _from (>=)."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"created_at_from": "2024-01-01"})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.created_at" in compiled  # noqa: S101
        assert ">=" in compiled  # noqa: S101

    def test_get_filtered_statement_with_to_filter(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Фильтр с суффиксом _to (<=)."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"created_at_to": "2024-12-31"})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.created_at" in compiled  # noqa: S101
        assert "<=" in compiled  # noqa: S101

    def test_get_filtered_statement_with_none_value(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Фильтр с None значением игнорируется."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"priority": None})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        # Не должно быть WHERE conditions
        assert "WHERE" not in compiled.upper() or compiled.upper().count(
            "WHERE"
        ) == compiled.upper().count(  # noqa: S101
            "FROM"
        )

    def test_get_filtered_statement_with_unknown_field(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Неизвестное поле игнорируется."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"unknown_field": "value"})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        # Не должно быть WHERE conditions
        assert "WHERE" not in compiled.upper() or compiled.upper().count(
            "WHERE"
        ) == compiled.upper().count(  # noqa: S101
            "FROM"
        )

    def test_get_filtered_statement_with_multiple_filters(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Несколько фильтров одновременно."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(
            stmt, {"priority": "HIGH", "status": "NEW", "created_at_from": "2024-01-01"}
        )
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.priority" in compiled  # noqa: S101
        assert "tasks.status" in compiled  # noqa: S101
        assert "tasks.created_at" in compiled  # noqa: S101
        assert ">=" in compiled  # noqa: S101

    def test_get_filtered_statement_with_empty_filters(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Пустой словарь фильтров — без изменений."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "WHERE" not in compiled.upper() or compiled.upper().count(
            "WHERE"
        ) == compiled.upper().count(  # noqa: S101
            "FROM"
        )
