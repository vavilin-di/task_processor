import logging
from asyncio import sleep

from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker

from src.services.outbox_messages import OutboxMessageService

from ..utilities import use_broker

logger = logging.getLogger(__name__)


async def run_outbox_publish_worker(container: AsyncContainer, poll_interval: float = 1.0) -> None:
    broker = await container.get(RabbitBroker)
    async with use_broker(broker, logger):
        while True:
            async with container() as request_container:
                outbox_messages_service = await request_container.get(OutboxMessageService)
                await outbox_messages_service.publish_batch()
            await sleep(poll_interval)
