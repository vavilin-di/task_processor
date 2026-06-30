from unittest.mock import AsyncMock, MagicMock

import pytest

from src.workers.task_processor.task_processor_worker import TaskProcessorWorker

pytestmark = pytest.mark.unit


class MockTaskService:
    """Простой мок для TaskService с асинхронными методами."""

    def __init__(self) -> None:
        self.process_task = AsyncMock()
        self.fail_task = AsyncMock()


@pytest.fixture
def mock_broker() -> AsyncMock:
    broker = AsyncMock()
    broker.subscriber = MagicMock()
    return broker


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    request_container = MagicMock()
    # container() возвращает request_container, async with на нём
    # вызывает request_container.__aenter__()
    container.return_value = request_container
    request_container.__aenter__ = AsyncMock(return_value=request_container)
    request_container.__aexit__ = AsyncMock()
    return container


@pytest.fixture
def mock_task_service() -> MockTaskService:
    return MockTaskService()


@pytest.fixture
def worker(
    mock_broker: AsyncMock,
    mock_container: MagicMock,
) -> TaskProcessorWorker:
    return TaskProcessorWorker(broker=mock_broker, container=mock_container)


class TestTaskProcessorWorker:
    """Unit-тесты для TaskProcessorWorker."""

    async def _setup_get(self, mock_container: MagicMock, mock_task_service: MockTaskService) -> None:
        """Настраивает request_container.get, чтобы он возвращал mock_task_service через await."""
        request_container = mock_container.return_value

        async def get_side_effect(*args: object, **kwargs: object) -> MockTaskService:
            return mock_task_service

        request_container.get = get_side_effect

    async def test_handle_message_calls_process_task(
        self,
        worker: TaskProcessorWorker,
        mock_container: MagicMock,
        mock_task_service: MockTaskService,
    ) -> None:
        """При получении сообщения с aggregate_id вызывается process_task."""
        await self._setup_get(mock_container, mock_task_service)

        await worker._handle_task_message({"aggregate_id": 1})

        mock_task_service.process_task.assert_awaited_once_with(1)
        mock_task_service.fail_task.assert_not_called()

    async def test_handle_message_calls_fail_task_on_error(
        self,
        worker: TaskProcessorWorker,
        mock_container: MagicMock,
        mock_task_service: MockTaskService,
    ) -> None:
        """При ошибке в process_task вызывается fail_task."""
        await self._setup_get(mock_container, mock_task_service)
        mock_task_service.process_task.side_effect = Exception("Processing error")

        await worker._handle_task_message({"aggregate_id": 1})

        mock_task_service.process_task.assert_awaited_once_with(1)
        mock_task_service.fail_task.assert_awaited_once_with(1)

    async def test_handle_message_skips_when_no_aggregate_id(
        self,
        worker: TaskProcessorWorker,
        mock_container: MagicMock,
        mock_task_service: MockTaskService,
    ) -> None:
        """Сообщение без aggregate_id игнорируется."""
        await self._setup_get(mock_container, mock_task_service)

        await worker._handle_task_message({"some_key": "value"})

        mock_task_service.process_task.assert_not_called()
        mock_task_service.fail_task.assert_not_called()

    async def test_handle_message_skips_when_task_not_found(
        self,
        worker: TaskProcessorWorker,
        mock_container: MagicMock,
        mock_task_service: MockTaskService,
    ) -> None:
        """Если задача не найдена (process_task вернул None), fail_task не вызывается."""
        await self._setup_get(mock_container, mock_task_service)
        mock_task_service.process_task.return_value = None

        await worker._handle_task_message({"aggregate_id": 999})

        mock_task_service.process_task.assert_awaited_once_with(999)
        mock_task_service.fail_task.assert_not_called()

    async def test_register_subscriber(
        self,
        worker: TaskProcessorWorker,
        mock_broker: AsyncMock,
    ) -> None:
        """Проверка, что subscriber регистрируется на TASKS_QUEUE."""
        worker._register_subscriber()

        mock_broker.subscriber.assert_called_once()
        assert worker._subscriber is not None  # noqa: S101


class TestGetTaskProcessorWorker:
    """Unit-тесты для get_task_processor_worker."""

    async def test_get_task_processor_worker_creates_worker(
        self,
    ) -> None:
        """get_task_processor_worker создаёт TaskProcessorWorker."""
        from src.workers.task_processor.task_processor_worker import get_task_processor_worker

        mock_container = MagicMock()
        mock_broker = AsyncMock()
        mock_container.get = AsyncMock(return_value=mock_broker)

        worker = await get_task_processor_worker(mock_container)

        assert worker is not None  # noqa: S101
        assert worker._broker is mock_broker  # noqa: S101
        assert worker._container is mock_container  # noqa: S101
