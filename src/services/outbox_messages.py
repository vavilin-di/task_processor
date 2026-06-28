import logging

from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from src.messaging.queues import TASKS_QUEUE
from src.repositories.outbox_messages import OutboxMessageRepository

logger = logging.getLogger(__name__)


class OutboxMessageService:

    def __init__(
        self, outbox_messages_repository: OutboxMessageRepository, broker: RabbitBroker, session: AsyncSession
    ) -> None:
        self._outbox_messages_repository = outbox_messages_repository
        self._broker = broker
        self._session = session

    async def publish_batch(self, limit: int = 10):
        async with self._session.begin():
            published_message_ids = []
            items = self._outbox_messages_repository.get_not_published_outbox_messages(limit)
            async for task_id, routing_key, payload in items:
                try:
                    await self._broker.publish(payload, TASKS_QUEUE, routing_key=routing_key)
                    published_message_ids.append(task_id)
                except Exception as ex:
                    logger.exception(
                        f"Произошла ошибка при публикации задачи с id {task_id} в брокере: {ex}", exc_info=ex
                    )
                    await self._outbox_messages_repository.add_error(task_id, str(ex))

            if len(published_message_ids) > 0:
                await self._outbox_messages_repository.mark_messages_as_published(published_message_ids)
