from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.models.outbox_messages import OutboxMessage
from src.repositories.outbox_messages import MAX_PUBLISH_ERRORS_COUNT, OutboxMessageRepository

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def outbox_repo(mock_session: AsyncMock) -> OutboxMessageRepository:
    with patch("src.repositories.outbox_messages.SQLAlchemyRepository.__init__", return_value=None):
        repo = OutboxMessageRepository.__new__(OutboxMessageRepository)
        repo._session = mock_session
        repo._model = OutboxMessage
        return repo


class TestOutboxMessageRepository:
    """Unit-тесты для OutboxMessageRepository с замокированным SQLAlchemyRepository."""

    async def _collect_from_stream(
        self, outbox_repo: OutboxMessageRepository, limit: int = 10
    ) -> list[tuple[int, str, dict[str, Any]]]:
        """Собирает результаты из асинхронного генератора."""
        return [item async for item in outbox_repo.get_not_published_outbox_messages(limit=limit)]

    async def test_get_not_published_outbox_messages(
        self, outbox_repo: OutboxMessageRepository, mock_session: AsyncMock
    ) -> None:
        # Настраиваем stream() чтобы он возвращал асинхронный итератор
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_stream
        mock_stream.__aiter__.return_value = iter(
            [
                MagicMock(tuple=lambda: (1, "task.created", {"key": "value"})),
                MagicMock(tuple=lambda: (2, "task.updated", {})),
            ]
        )
        mock_session.stream.return_value = mock_stream

        result = await self._collect_from_stream(outbox_repo)
        assert result == [(1, "task.created", {"key": "value"}), (2, "task.updated", {})]  # noqa: S101
        mock_session.stream.assert_awaited_once()

    async def test_get_not_published_outbox_messages_empty(
        self, outbox_repo: OutboxMessageRepository, mock_session: AsyncMock
    ) -> None:
        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_stream
        mock_stream.__aiter__.return_value = iter([])
        mock_session.stream.return_value = mock_stream

        result = await self._collect_from_stream(outbox_repo)
        assert result == []  # noqa: S101

    async def test_mark_messages_as_published(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        await outbox_repo.mark_messages_as_published(message_ids=[1, 2])
        mock_session.execute.assert_awaited_once()  # type: ignore[attr-defined]

    async def test_add_error_below_threshold(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ["previous error"]
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        await outbox_repo.add_error(task_id=1, error="Some error")

        assert mock_session.execute.await_count == 1  # type: ignore[attr-defined] # noqa: S101

    async def test_add_error_exceeds_threshold_marks_failed(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = list(range(MAX_PUBLISH_ERRORS_COUNT))
        mock_session.execute.side_effect = [mock_result, mock_result]  # type: ignore[attr-defined]

        await outbox_repo.add_error(task_id=1, error="Fatal error")

        # Должно быть два execute: update с returning + update is_failed=True
        assert mock_session.execute.await_count == 2  # type: ignore[attr-defined] # noqa: S101, PLR2004

    async def test_add_error_raises_on_none_errors_count(self, outbox_repo: OutboxMessageRepository) -> None:
        mock_session = outbox_repo._session
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result  # type: ignore[attr-defined]

        with pytest.raises(AssertionError, match="OutboxMessage с id=1 не найдено"):
            await outbox_repo.add_error(task_id=1, error="Error")
