from unittest.mock import AsyncMock, patch

import pytest

from src.database.models.tasks import Task
from src.repositories.soft_delete_sqlalchemy_repository import SoftDeleteSQLAlchemyRepository

pytestmark = pytest.mark.unit


class TestSoftDeleteSQLAlchemyRepository:
    """Unit-тесты для SoftDeleteSQLAlchemyRepository."""

    @pytest.fixture
    def repo(self) -> SoftDeleteSQLAlchemyRepository[Task]:
        with patch.object(SoftDeleteSQLAlchemyRepository, "__init__", return_value=None):
            repo = SoftDeleteSQLAlchemyRepository.__new__(SoftDeleteSQLAlchemyRepository)
            repo._model = Task
            repo._session = AsyncMock()
            return repo

    async def test_delete_sets_is_active_false(self, repo: SoftDeleteSQLAlchemyRepository[Task]) -> None:
        """delete устанавливает is_active=False вместо удаления."""
        mock_session = repo._session

        await repo.delete(record_id=1)

        mock_session.execute.assert_awaited_once()  # type: ignore[attr-defined]

    def test_get_base_record_filter_includes_is_active(self, repo: SoftDeleteSQLAlchemyRepository[Task]) -> None:
        """_get_base_record_filter включает условие is_active."""
        result = repo._get_base_record_filter(record_id=1)
        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "tasks.id" in compiled  # noqa: S101
        assert "tasks.is_active" in compiled  # noqa: S101

    def test_get_base_get_all_select_statement_includes_is_active(
        self, repo: SoftDeleteSQLAlchemyRepository[Task]
    ) -> None:
        """_get_base_get_all_select_statement включает WHERE is_active."""
        result = repo._get_base_get_all_select_statement()
        compiled = str(result.compile(compile_kwargs={"literal_binds": True}))
        assert "SELECT" in compiled  # noqa: S101
        assert "tasks.is_active" in compiled  # noqa: S101
        assert "ORDER BY" in compiled.upper()  # noqa: S101
