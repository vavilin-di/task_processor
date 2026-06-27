import asyncio
import logging

from src.di import create_di_container

from .dlq_consumer_worker import get_dlq_consumer_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    container = create_di_container()
    try:
        dlq_consumer_worker = await get_dlq_consumer_worker(container)
        await dlq_consumer_worker.run()
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
