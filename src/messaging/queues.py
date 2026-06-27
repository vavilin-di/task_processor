from uuid import uuid4

from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

TASKS_MESSAGE_TTL_MS = 600_000  # 10 минут
TASKS_MAX_MESSAGES_COUNT = 10_000
RETRY_EXPIRATION_DELAY_MS = 10_000

ROUTING_KEY_PROCESS = "process"
ROUTING_KEY_FAILED = "failed"

TASKS_DLX_EXCHANGE_NAME = "tasks_dlx"
DLQ_RECOVER_QUEUE_PREFIX = "dlq_recover"

# Exchanges
TASKS_EXCHANGE = RabbitExchange(name="tasks_exchange", type=ExchangeType.DIRECT, durable=True)
TASKS_DLX_EXCHANGE = RabbitExchange(name=TASKS_DLX_EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)

# Queues
TASKS_QUEUE = RabbitQueue(
    name="task_processing",
    routing_key=ROUTING_KEY_PROCESS,
    durable=True,
    arguments={
        "x-dead-letter-exchange": TASKS_DLX_EXCHANGE_NAME,
        "x-dead-letter-routing-key": ROUTING_KEY_FAILED,
        "x-message-ttl": TASKS_MESSAGE_TTL_MS,
        "x-max-length": TASKS_MAX_MESSAGES_COUNT,
    },
)
TASKS_DLQ_QUEUE = RabbitQueue(name="task_processing_dlq", routing_key=ROUTING_KEY_FAILED, durable=True)


def get_retry_queue(delay_ms: float) -> RabbitQueue:
    """Создаёт временную очередь для retry с указанной задержкой"""
    return RabbitQueue(
        name=f"{DLQ_RECOVER_QUEUE_PREFIX}_{uuid4().hex}",
        durable=False,
        arguments={
            "x-dead-letter-exchange": TASKS_EXCHANGE.name,
            "x-dead-letter-routing-key": ROUTING_KEY_PROCESS,
            "x-message-ttl": delay_ms,
            "x-expires": delay_ms + RETRY_EXPIRATION_DELAY_MS,
        },
    )
