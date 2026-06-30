from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.outbox_messages import OutboxCleanupService, OutboxMessageService

pytestmark = pytest.mark.unit


async def _async_gen_from_list(items: list) -> AsyncGenerator:
    """Создаёт асинхронный генератор из списка для мока."""
    for item in items:
        yield item


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    begin_context = AsyncMock()
    begin_context.__aenter__ = AsyncMock()
    begin_context.__aexit__ = AsyncMock()
    session.begin = MagicMock(return_value=begin_context)
    return session


@pytest.fixture
def mock_broker() -> AsyncMock:
    broker = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def mock_repo() -> MagicMock:
    """Репозиторий с методами, возвращающими асинхронные генераторы."""
    repo = MagicMock()
    repo.get_not_published_outbox_messages = MagicMock()
    repo.mark_messages_as_published = AsyncMock()
    repo.add_error = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session: MagicMock, mock_broker: AsyncMock, mock_repo: MagicMock) -> OutboxMessageService:
    return OutboxMessageService(outbox_messages_repository=mock_repo, broker=mock_broker, session=mock_session)


class TestOutboxMessageService:
    """Unit-тесты для OutboxMessageService.publish_batch."""

    async def test_publishes_all_messages(
        self,
        service: OutboxMessageService,
        mock_repo: MagicMock,
        mock_broker: AsyncMock,
    ) -> None:
        """Два сообщения — оба должны быть опубликованы и отмечены."""
        mock_repo.get_not_published_outbox_messages.return_value = _async_gen_from_list(
            [
                (1, "task.created", {"key": "value"}),
                (2, "task.updated", {}),
            ]
        )

        await service.publish_batch()

        assert mock_broker.publish.await_count == 2  # noqa: S101, PLR2004
        mock_repo.mark_messages_as_published.assert_awaited_once_with([1, 2])
        mock_repo.add_error.assert_not_called()

    async def test_handles_publish_error(
        self,
        service: OutboxMessageService,
        mock_repo: MagicMock,
        mock_broker: AsyncMock,
    ) -> None:
        """При ошибке публикации вызывается add_error, но сообщение не отмечается как опубликованное."""
        mock_repo.get_not_published_outbox_messages.return_value = _async_gen_from_list(
            [
                (1, "task.created", {"key": "value"}),
            ]
        )
        mock_broker.publish.side_effect = Exception("Connection lost")

        await service.publish_batch()

        mock_repo.add_error.assert_awaited_once_with(1, "Connection lost")
        mock_repo.mark_messages_as_published.assert_not_called()

    async def test_empty_batch_does_nothing(
        self,
        service: OutboxMessageService,
        mock_repo: MagicMock,
        mock_broker: AsyncMock,
    ) -> None:
        """Нет сообщений — ничего не публикуем."""
        mock_repo.get_not_published_outbox_messages.return_value = _async_gen_from_list([])

        await service.publish_batch()

        mock_broker.publish.assert_not_called()
        mock_repo.mark_messages_as_published.assert_not_called()
        mock_repo.add_error.assert_not_called()

    async def test_partial_publish_error(
        self,
        service: OutboxMessageService,
        mock_repo: MagicMock,
        mock_broker: AsyncMock,
    ) -> None:
        """Первое сообщение падает с ошибкой, второе публикуется успешно."""
        mock_repo.get_not_published_outbox_messages.return_value = _async_gen_from_list(
            [
                (1, "task.created", {"a": 1}),
                (2, "task.updated", {"b": 2}),
            ]
        )
        mock_broker.publish.side_effect = [Exception("Timeout"), None]

        await service.publish_batch()

        mock_repo.add_error.assert_awaited_once_with(1, "Timeout")
        mock_repo.mark_messages_as_published.assert_awaited_once_with([2])


@pytest.fixture
def mock_cleanup_repo() -> AsyncMock:
    """Репозиторий для OutboxCleanupService."""
    repo = AsyncMock()
    repo.delete_published_older_than = AsyncMock()
    return repo


@pytest.fixture
def cleanup_service(mock_session: MagicMock, mock_cleanup_repo: AsyncMock) -> OutboxCleanupService:
    return OutboxCleanupService(outbox_messages_repository=mock_cleanup_repo, session=mock_session)


class TestOutboxCleanupService:
    """Unit-тесты для OutboxCleanupService.cleanup."""

    async def test_cleanup__deletes_expired_messages(
        self,
        cleanup_service: OutboxCleanupService,
        mock_cleanup_repo: AsyncMock,
    ) -> None:
        """Успешное удаление — возвращается количество удалённых записей."""
        mock_cleanup_repo.delete_published_older_than.return_value = 42

        deleted = await cleanup_service.cleanup(ttl_hours=24, batch_size=100)

        assert deleted == 42  # noqa: S101, PLR2004
        mock_cleanup_repo.delete_published_older_than.assert_awaited_once_with(24, 100)

    async def test_cleanup__nothing_to_delete(
        self,
        cleanup_service: OutboxCleanupService,
        mock_cleanup_repo: AsyncMock,
    ) -> None:
        """Нет сообщений для удаления — возвращается 0."""
        mock_cleanup_repo.delete_published_older_than.return_value = 0

        deleted = await cleanup_service.cleanup(ttl_hours=24, batch_size=100)

        assert deleted == 0  # noqa: S101
        mock_cleanup_repo.delete_published_older_than.assert_awaited_once_with(24, 100)
