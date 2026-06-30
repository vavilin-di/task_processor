import pytest

from src.messaging.queues import (
    DLQ_RECOVER_QUEUE_PREFIX,
    RETRY_EXPIRATION_DELAY_MS,
    ROUTING_KEY_FAILED,
    ROUTING_KEY_PROCESS,
    TASKS_DLQ_QUEUE,
    TASKS_DLX_EXCHANGE,
    TASKS_DLX_EXCHANGE_NAME,
    TASKS_EXCHANGE,
    TASKS_MAX_MESSAGES_COUNT,
    TASKS_MESSAGE_TTL_MS,
    TASKS_QUEUE,
    get_retry_queue,
)

pytestmark = pytest.mark.unit


class TestQueuesConstants:
    """Тесты для констант модуля queues."""

    def test_message_ttl(self) -> None:
        assert TASKS_MESSAGE_TTL_MS == 600_000  # noqa: S101, PLR2004

    def test_max_messages_count(self) -> None:
        assert TASKS_MAX_MESSAGES_COUNT == 10_000  # noqa: S101, PLR2004

    def test_retry_expiration_delay(self) -> None:
        assert RETRY_EXPIRATION_DELAY_MS == 10_000  # noqa: S101, PLR2004

    def test_routing_keys(self) -> None:
        assert ROUTING_KEY_PROCESS == "process"  # noqa: S101
        assert ROUTING_KEY_FAILED == "failed"  # noqa: S101

    def test_dlx_exchange_name(self) -> None:
        assert TASKS_DLX_EXCHANGE_NAME == "tasks_dlx"  # noqa: S101

    def test_dlq_recover_queue_prefix(self) -> None:
        assert DLQ_RECOVER_QUEUE_PREFIX == "dlq_recover"  # noqa: S101


class TestExchanges:
    """Тесты для RabbitExchange."""

    def test_tasks_exchange(self) -> None:
        assert TASKS_EXCHANGE.name == "tasks_exchange"  # noqa: S101

    def test_tasks_dlx_exchange(self) -> None:
        assert TASKS_DLX_EXCHANGE.name == TASKS_DLX_EXCHANGE_NAME  # noqa: S101


class TestQueues:
    """Тесты для RabbitQueue."""

    def test_tasks_queue_name(self) -> None:
        assert TASKS_QUEUE.name == "task_processing"  # noqa: S101

    def test_tasks_queue_routing_key(self) -> None:
        assert TASKS_QUEUE.routing_key == ROUTING_KEY_PROCESS  # noqa: S101

    def test_tasks_queue_arguments(self) -> None:
        assert TASKS_QUEUE.arguments["x-dead-letter-exchange"] == TASKS_DLX_EXCHANGE_NAME  # noqa: S101
        assert TASKS_QUEUE.arguments["x-dead-letter-routing-key"] == ROUTING_KEY_FAILED  # noqa: S101
        assert TASKS_QUEUE.arguments["x-message-ttl"] == TASKS_MESSAGE_TTL_MS  # noqa: S101
        assert TASKS_QUEUE.arguments["x-max-length"] == TASKS_MAX_MESSAGES_COUNT  # noqa: S101

    def test_tasks_dlq_queue_name(self) -> None:
        assert TASKS_DLQ_QUEUE.name == "task_processing_dlq"  # noqa: S101

    def test_tasks_dlq_queue_routing_key(self) -> None:
        assert TASKS_DLQ_QUEUE.routing_key == ROUTING_KEY_FAILED  # noqa: S101


class TestGetRetryQueue:
    """Тесты для get_retry_queue."""

    def test_retry_queue_name_starts_with_prefix(self) -> None:
        queue = get_retry_queue(delay_ms=5_000)
        assert queue.name.startswith(DLQ_RECOVER_QUEUE_PREFIX)  # noqa: S101

    def test_retry_queue_not_durable(self) -> None:
        queue = get_retry_queue(delay_ms=5_000)
        assert queue.durable is False  # noqa: S101

    def test_retry_queue_arguments(self) -> None:
        delay_ms = 5_000
        queue = get_retry_queue(delay_ms=delay_ms)

        assert queue.arguments["x-dead-letter-exchange"] == TASKS_EXCHANGE.name  # noqa: S101
        assert queue.arguments["x-dead-letter-routing-key"] == ROUTING_KEY_PROCESS  # noqa: S101
        assert queue.arguments["x-message-ttl"] == delay_ms  # noqa: S101
        assert queue.arguments["x-expires"] == delay_ms + RETRY_EXPIRATION_DELAY_MS  # noqa: S101

    def test_retry_queue_unique_names(self) -> None:
        queue1 = get_retry_queue(delay_ms=5_000)
        queue2 = get_retry_queue(delay_ms=5_000)
        assert queue1.name != queue2.name  # noqa: S101
