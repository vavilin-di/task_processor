__all__ = ["get_dlq_consumer_worker"]

import asyncio
import logging

from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from src.messaging.queues import ROUTING_KEY_PROCESS, TASKS_DLQ_QUEUE, get_retry_queue
from src.repositories.dlq_messages import DLQMessageRepository
from src.schemas.dlq_messages import DLQMessage, DLQMessageCreate

from ..utilities import use_broker

logger = logging.getLogger(__name__)

MAX_DLQ_RETRIES = 3
DELAY_INCREMENT_SEC = 5

RETRY_DELAYS_MSEC = [retry_num * DELAY_INCREMENT_SEC * 1000 for retry_num in range(1, MAX_DLQ_RETRIES + 1)]


class DLQConsumerWorker:

    def __init__(self, broker: RabbitBroker, container: AsyncContainer) -> None:
        self._broker = broker
        self._container = container

    async def run(self) -> None:
        async with use_broker(self._broker, logger):
            await self._register_subscriber()
            await asyncio.Future()

    async def _register_subscriber(self) -> None:
        @self._broker.subscriber(TASKS_DLQ_QUEUE)
        async def handle_dlq_message(raw_message: dict) -> None:
            message = DLQMessage(**raw_message)
            retry_count = 0 if message.x_death is None else len(message.x_death)
            if retry_count < MAX_DLQ_RETRIES:
                await self._retry(message, retry_count)
                return
            await self._log_failure_to_db(message, retry_count)

            logger.info(f"DLQ: исчерпано количество повторов после {retry_count} попыток")

    async def _retry(self, message: DLQMessage, retry_count: int) -> None:
        delay = RETRY_DELAYS_MSEC[retry_count]
        retry_queue = get_retry_queue(delay)
        await self._broker.publish(message=message.original_payload, queue=retry_queue)
        logger.info(f"DLQ: отправлено в очередь повторов {retry_count + 1}/{MAX_DLQ_RETRIES}")

    async def _log_failure_to_db(self, message: DLQMessage, retry_count: int) -> None:
        async with self._container() as request_container:
            session = await request_container.get(AsyncSession)
            dlq_repository = await request_container.get(DLQMessageRepository)
            dlq_table_message = DLQMessageCreate(
                original_routing_key=ROUTING_KEY_PROCESS,
                original_payload=message.original_payload,
                error_type=message.error_type,
                error_message=message.error_message,
                retry_count=retry_count,
                x_death=message.x_death,
            )
            await dlq_repository.create(**dlq_table_message.model_dump())
            await session.commit()


async def get_dlq_consumer_worker(container: AsyncContainer) -> DLQConsumerWorker:
    broker = await container.get(RabbitBroker)
    return DLQConsumerWorker(broker, container)
