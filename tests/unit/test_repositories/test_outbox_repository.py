from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.repositories.outbox_messages import MAX_PUBLISH_ERRORS_COUNT, OutboxMessageRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def outbox_repo(mock_session: AsyncMock) -> OutboxMessageRepository:
    with patch("src.repositories.outbox_messages.SQLAlchemyRepository.__init__", return_value=None):
        repo = OutboxMessageRepository.__new__(OutboxMessageRepository)
        repo._session = mock_session
        repo._model = MagicMock()
        repo._model.id = PropertyMock()
        repo._model.routing_key = PropertyMock()
        repo._model.is_published = PropertyMock()
        repo._model.is_failed = PropertyMock()
        repo._model.created_at = PropertyMock()
        return repo


class TestOutboxMessageRepository:
    """Unit-тесты для OutboxMessageRepository с замокированным SQLAlchemyRepository."""

    async def test_get_not_published_outbox_messages(
        self, outbox_repo: OutboxMessageRepository, mock_session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.t.all.return_value = [(1, "task.created", {"key": "value"}), (2, "task.updated", {})]
        mock_session.execute.return_value = mock_result

        result = await outbox_repo.get_not_published_outbox_messages(limit=10)
        assert result == [(1, "task.created", {"key": "value"}), (2, "task.updated", {})]  # noqa: S101
        mock_session.execute.assert_awaited_once()

    async def test_get_not_published_outbox_messages_empty(
        self, outbox_repo: OutboxMessageRepository, mock_session: AsyncMock
    ) -> None:
        mock_result = MagicMock()
        mock_result.t.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await outbox_repo.get_not_published_outbox_messages(limit=10)
        assert result == []  # noqa: S101

    async def test_mark_messages_as_published(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        await outbox_repo.mark_messages_as_published(message_ids=[1, 2])
        mock_session.execute.assert_awaited_once()

    async def test_add_error_below_threshold(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ["previous error"]
        mock_session.execute.return_value = mock_result

        await outbox_repo.add_error(task_id=1, error="Some error")

        assert mock_session.execute.await_count == 1  # noqa: S101, PLR2004

    async def test_add_error_exceeds_threshold_marks_failed(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = list(range(MAX_PUBLISH_ERRORS_COUNT))
        mock_session.execute.side_effect = [mock_result, mock_result]

        await outbox_repo.add_error(task_id=1, error="Fatal error")

        # Должно быть два execute: update с returning + update is_failed=True
        assert mock_session.execute.await_count == 2  # noqa: S101, PLR2004

    async def test_add_error_raises_on_none_errors_count(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(AssertionError, match="OutboxMessage с id=1 не найдено"):
            await outbox_repo.add_error(task_id=1, error="Error")
