from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.messaging.queues import TASKS_DLQ_QUEUE
from src.schemas.dlq_messages import DLQMessage
from src.workers.dlq_consumer.dlq_consumer_worker import (
    MAX_DLQ_RETRIES,
    DLQConsumerWorker,
    get_dlq_consumer_worker,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_broker() -> AsyncMock:
    broker = AsyncMock()
    broker.subscriber = MagicMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    request_container = MagicMock()
    container.return_value = request_container
    request_container.__aenter__ = AsyncMock(return_value=request_container)
    request_container.__aexit__ = AsyncMock()
    return container


@pytest.fixture
def worker(mock_broker: AsyncMock, mock_container: MagicMock) -> DLQConsumerWorker:
    return DLQConsumerWorker(broker=mock_broker, container=mock_container)


def _make_dlq_message(**overrides: object) -> DLQMessage:
    """Create DLQMessage with default fields."""
    data: dict[str, object] = {
        "id": 1,
        "original_routing_key": "test",
        "original_payload": {"key": "value"},
        "error_type": "Error",
        "error_message": "Msg",
        "retry_count": 0,
        "x_death": None,
        "created_at": datetime.now(UTC),
    }
    data.update(overrides)
    return DLQMessage(**data)


class TestDLQConsumerWorker:
    """Unit tests for DLQConsumerWorker."""

    def test_register_subscriber(self, worker: DLQConsumerWorker, mock_broker: AsyncMock) -> None:
        """Verify subscriber registration on TASKS_DLQ_QUEUE."""
        worker._register_subscriber()

        mock_broker.subscriber.assert_called_once_with(TASKS_DLQ_QUEUE)
        assert worker._subscriber is not None  # noqa: S101

    async def test_handle_message_with_retries_remaining(
        self, worker: DLQConsumerWorker, mock_broker: AsyncMock
    ) -> None:
        """Message with x_death < MAX_DLQ_RETRIES is sent to retry."""
        raw_message = _make_dlq_message(
            x_death=[{"count": 1, "reason": "rejected"}],
        ).model_dump()

        with patch("src.workers.dlq_consumer.dlq_consumer_worker.get_retry_queue") as mock_get_retry:
            mock_queue = MagicMock()
            mock_get_retry.return_value = mock_queue
            await worker._handle_dlq_message(raw_message)

        mock_broker.publish.assert_awaited_once()
        mock_get_retry.assert_called_once()

    async def test_handle_message_exhausted_retries(self, worker: DLQConsumerWorker, mock_container: MagicMock) -> None:
        """Message with x_death >= MAX_DLQ_RETRIES is logged to DB."""
        raw_message = _make_dlq_message(
            x_death=[{"count": 1, "reason": "rejected"}] * MAX_DLQ_RETRIES,
        ).model_dump()

        request_container = mock_container.return_value
        mock_session = AsyncMock()
        mock_dlq_repo = AsyncMock()

        async def get_side_effect(cls: object) -> object:
            name = getattr(cls, "__name__", str(cls))
            if "AsyncSession" in name:
                return mock_session
            if "DLQMessageRepository" in name:
                return mock_dlq_repo
            msg = f"Unexpected class: {cls}"
            raise ValueError(msg)

        request_container.get = get_side_effect

        await worker._handle_dlq_message(raw_message)

        mock_dlq_repo.create.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_handle_message_no_x_death(self, worker: DLQConsumerWorker, mock_broker: AsyncMock) -> None:
        """Message without x_death has retry_count=0, sent to retry."""
        raw_message = _make_dlq_message(x_death=None).model_dump()

        with patch("src.workers.dlq_consumer.dlq_consumer_worker.get_retry_queue") as mock_get_retry:
            mock_queue = MagicMock()
            mock_get_retry.return_value = mock_queue
            await worker._handle_dlq_message(raw_message)

        mock_broker.publish.assert_awaited_once()

    async def test_retry_publishes_to_retry_queue(self, worker: DLQConsumerWorker, mock_broker: AsyncMock) -> None:
        """_retry publishes message to retry queue."""
        message = _make_dlq_message()

        with patch("src.workers.dlq_consumer.dlq_consumer_worker.get_retry_queue") as mock_get_retry:
            mock_queue = MagicMock()
            mock_get_retry.return_value = mock_queue
            await worker._retry(message, retry_count=0)

        mock_broker.publish.assert_awaited_once_with(message=message.original_payload, queue=mock_queue)

    async def test_log_failure_to_db_creates_record(self, worker: DLQConsumerWorker, mock_container: MagicMock) -> None:
        """_log_failure_to_db creates DLQ record and commits."""
        message = _make_dlq_message()

        request_container = mock_container.return_value
        mock_session = AsyncMock()
        mock_dlq_repo = AsyncMock()

        async def get_side_effect(cls: object) -> object:
            name = getattr(cls, "__name__", str(cls))
            if "AsyncSession" in name:
                return mock_session
            if "DLQMessageRepository" in name:
                return mock_dlq_repo
            msg = f"Unexpected class: {cls}"
            raise ValueError(msg)

        request_container.get = get_side_effect

        await worker._log_failure_to_db(message, retry_count=3)

        mock_dlq_repo.create.assert_awaited_once()
        mock_session.commit.assert_awaited_once()


class TestGetDLQConsumerWorker:
    """Unit tests for get_dlq_consumer_worker."""

    async def test_get_dlq_consumer_worker_creates_worker(self) -> None:
        """get_dlq_consumer_worker creates DLQConsumerWorker."""
        mock_container = MagicMock()
        mock_broker = AsyncMock()
        mock_container.get = AsyncMock(return_value=mock_broker)

        worker = await get_dlq_consumer_worker(mock_container)

        assert worker is not None  # noqa: S101
        assert worker._broker is mock_broker  # noqa: S101
        assert worker._container is mock_container  # noqa: S101
