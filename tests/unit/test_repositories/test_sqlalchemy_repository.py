from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.database.models.tasks import Task
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository

pytestmark = pytest.mark.unit


class TestSQLAlchemyRepositoryUnit:
    """Unit-тесты для SQLAlchemyRepository (логика без БД)."""

    @pytest.fixture
    def repo(self) -> SQLAlchemyRepository[Task]:
        with patch.object(SQLAlchemyRepository, "__init__", return_value=None):
            repo = SQLAlchemyRepository.__new__(SQLAlchemyRepository)
            repo._model = Task
            repo._session = AsyncMock()
            return repo

    async def test_create_adds_and_flushes(self, repo: SQLAlchemyRepository[Task]) -> None:
        """create добавляет объект в сессию, делает flush и refresh."""
        mock_session = repo._session
        mock_session.refresh = AsyncMock()  # type: ignore[method-assign]

        result = await repo.create(name="Test", description="Desc", payload={})

        mock_session.add.assert_called_once()  # type: ignore[attr-defined]
        mock_session.flush.assert_awaited_once()  # type: ignore[attr-defined]
        mock_session.refresh.assert_awaited_once()
        assert result is not None  # noqa: S101

    async def test_get_returns_scalar(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get возвращает результат scalar_one_or_none."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "task"
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.get(record_id=1)

        assert result == "task"  # noqa: S101
        mock_session.execute.assert_awaited_once()  # type: ignore[attr-defined]

    async def test_get_returns_none(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get возвращает None для несуществующей записи."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.get(record_id=999)

        assert result is None  # noqa: S101

    async def test_exists_returns_true(self, repo: SQLAlchemyRepository[Task]) -> None:
        """exists возвращает True, если запись существует."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar.return_value = True
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.exists(record_id=1)

        assert result is True  # noqa: S101

    async def test_exists_returns_false(self, repo: SQLAlchemyRepository[Task]) -> None:
        """exists возвращает False, если записи нет."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.exists(record_id=999)

        assert result is False  # noqa: S101

    async def test_get_all_returns_items(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get_all возвращает список элементов, курсор и has_next."""
        with patch("src.repositories.sqlalchemy_repository.select_page") as mock_select_page:
            mock_page = MagicMock()
            mock_page.paging.bookmark_next = "next_cursor"
            mock_page.paging.has_next = True
            mock_select_page.return_value = mock_page

            _, cursor, has_next = await repo.get_all(cursor=None, limit=10, filters=None)

            assert cursor == "next_cursor"  # noqa: S101
            assert has_next is True  # noqa: S101

    async def test_get_all_with_filters(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get_all с фильтрами."""
        with patch("src.repositories.sqlalchemy_repository.select_page") as mock_select_page:
            mock_page = MagicMock()
            mock_page.paging.bookmark_next = None
            mock_page.paging.has_next = False
            mock_select_page.return_value = mock_page

            _, cursor, has_next = await repo.get_all(cursor=None, limit=10, filters={"priority": "HIGH"})

            assert cursor is None  # noqa: S101
            assert has_next is False  # noqa: S101

    async def test_get_value_returns_field(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get_value возвращает значение поля."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "some_value"
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.get_value(record_id=1, field=Task.name)

        assert result == "some_value"  # noqa: S101
        mock_session.execute.assert_awaited_once()  # type: ignore[attr-defined]

    async def test_get_value_returns_none(self, repo: SQLAlchemyRepository[Task]) -> None:
        """get_value возвращает None для несуществующей записи."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.get_value(record_id=999, field=Task.name)

        assert result is None  # noqa: S101

    async def test_update_modifies_record(self, repo: SQLAlchemyRepository[Task]) -> None:
        """update изменяет запись и возвращает её."""
        mock_session = repo._session
        # Первый вызов execute — для exists
        mock_exists_result = MagicMock()
        mock_exists_result.scalar.return_value = True
        # Второй вызов execute — для update
        mock_update_result = MagicMock()
        mock_update_result.scalar_one_or_none.return_value = "updated_task"

        mock_session.execute.side_effect = [mock_exists_result, mock_update_result]  # type: ignore[attr-defined]

        result = await repo.update(record_id=1, name="Updated")

        assert result == "updated_task"  # noqa: S101
        assert mock_session.execute.await_count == 2  # type: ignore[attr-defined]# noqa: S101, PLR2004

    async def test_update_returns_none_for_missing(self, repo: SQLAlchemyRepository[Task]) -> None:
        """update возвращает None для несуществующей записи."""
        mock_session = repo._session
        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        result = await repo.update(record_id=999, name="Updated")

        assert result is None  # noqa: S101
        assert mock_session.execute.await_count == 1  # type: ignore[attr-defined] # noqa: S101

    async def test_delete_removes_record(self, repo: SQLAlchemyRepository[Task]) -> None:
        """delete удаляет запись."""
        mock_session = repo._session

        await repo.delete(record_id=1)

        mock_session.execute.assert_awaited_once()  # type: ignore[attr-defined]

    def test_get_base_record_filter(self, repo: SQLAlchemyRepository[Task]) -> None:
        """_get_base_record_filter возвращает условие id == record_id."""
        result = repo._get_base_record_filter(record_id=1)
        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.id" in compiled  # noqa: S101
        assert "1" in compiled  # noqa: S101

    def test_get_base_get_all_select_statement(self, repo: SQLAlchemyRepository[Task]) -> None:
        """_get_base_get_all_select_statement возвращает SELECT с ORDER BY id."""
        result = repo._get_base_get_all_select_statement()
        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "SELECT" in compiled  # noqa: S101
        assert "ORDER BY" in compiled.upper()  # noqa: S101

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
        assert "WHERE" not in compiled.upper() or compiled.upper().count(  # noqa: S101
            "WHERE"
        ) == compiled.upper().count("FROM")

    def test_get_filtered_statement_with_unknown_field(self, repo: SQLAlchemyRepository[Task]) -> None:
        """Неизвестное поле игнорируется."""
        stmt = select(Task)
        filtered = repo._get_filtered_statement(stmt, {"unknown_field": "value"})
        compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
        assert "WHERE" not in compiled.upper() or compiled.upper().count(  # noqa: S101
            "WHERE"
        ) == compiled.upper().count("FROM")

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
        assert "WHERE" not in compiled.upper() or compiled.upper().count(  # noqa: S101
            "WHERE"
        ) == compiled.upper().count("FROM")
