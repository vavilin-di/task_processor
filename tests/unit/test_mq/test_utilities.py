from asyncio import CancelledError
from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.workers.utilities import use_broker


@pytest.fixture
def mock_broker() -> AsyncMock:
    broker = AsyncMock()
    broker.start = AsyncMock()
    broker.stop = AsyncMock()
    return broker


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock(spec=Logger)


class TestUseBroker:
    """Тесты для контекстного менеджера use_broker."""

    async def test_starts_and_stops_broker(self, mock_broker: AsyncMock, mock_logger: MagicMock) -> None:
        async with use_broker(mock_broker, mock_logger):
            pass

        mock_broker.start.assert_awaited_once()
        mock_broker.stop.assert_awaited_once()

    async def test_stops_broker_on_exception(self, mock_broker: AsyncMock, mock_logger: MagicMock) -> None:
        with pytest.raises(RuntimeError, match="Test error"):
            async with use_broker(mock_broker, mock_logger):
                msg = "Test error"
                raise RuntimeError(msg)

        mock_broker.start.assert_awaited_once()
        mock_broker.stop.assert_awaited_once()

    async def test_stops_broker_on_cancelled_error(self, mock_broker: AsyncMock, mock_logger: MagicMock) -> None:
        with pytest.raises(CancelledError):
            async with use_broker(mock_broker, mock_logger):
                raise CancelledError()

        mock_broker.start.assert_awaited_once()
        mock_broker.stop.assert_awaited_once()
