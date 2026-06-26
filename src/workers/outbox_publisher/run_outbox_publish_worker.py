import asyncio
import logging

from src.di import create_di_container
from src.workers.outbox_publisher.outbox_publish_worker import run_outbox_publish_worker

logging.basicConfig(level=logging.INFO)


async def main():
    container = create_di_container()
    try:
        await run_outbox_publish_worker(container, poll_interval=0.5)
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
