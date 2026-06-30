import logging
from asyncio import sleep

from dishka import AsyncContainer

from src.services.outbox_messages import OutboxCleanupService
from src.settings import Settings

logger = logging.getLogger(__name__)


async def run_outbox_cleanup_worker(container: AsyncContainer) -> None:
    settings = await container.get(Settings)
    while True:
        async with container() as request_container:
            cleanup_service = await request_container.get(OutboxCleanupService)
            deleted_messages_count = await cleanup_service.cleanup(
                settings.OUTBOX_TTL_HRS, settings.OUTBOX_CLEANUP_BATCH_SIZE
            )
            if deleted_messages_count:
                logger.info(f"Удалено {deleted_messages_count} устаревших outbox-сообщений")
        await sleep(settings.OUTBOX_CLEANUP_INTERVAL_SEC)
