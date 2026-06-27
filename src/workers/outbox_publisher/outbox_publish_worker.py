import logging
from asyncio import sleep

from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from src.messaging.queues import TASKS_QUEUE
from src.repositories.outbox_messages import OutboxMessageRepository

from ..utilities import use_broker

logger = logging.getLogger(__name__)


async def process_batch(
    session: AsyncSession, broker: RabbitBroker, outbox_messages_repo: OutboxMessageRepository
) -> None:
    async with session.begin():
        get_not_published_tasks = await outbox_messages_repo.get_not_published_tasks()
        for task in get_not_published_tasks:
            try:
                await broker.publish(task.payload, TASKS_QUEUE, routing_key=task.routing_key)
                await outbox_messages_repo.mark_task_as_published(task.id)
            except Exception as ex:
                logger.error(f"Произошла ошибка при публикации задачи с id {task.id} в брокере: {ex}")
                await outbox_messages_repo.add_error(task.id, str(ex))


async def run_outbox_publish_worker(container: AsyncContainer, poll_interval: float = 1.0) -> None:
    broker = await container.get(RabbitBroker)
    async with use_broker(broker, logger):
        while True:
            async with container() as request_container:
                session = await request_container.get(AsyncSession)
                outbox_messages_repo = await request_container.get(OutboxMessageRepository)
                await process_batch(session, broker, outbox_messages_repo)
            await sleep(poll_interval)
