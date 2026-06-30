import asyncio
import logging

from src.di import create_di_container
from src.workers.task_processor.task_processor_worker import get_task_processor_worker

logging.basicConfig(level=logging.INFO)


async def main():
    container = create_di_container()
    try:
        worker = await get_task_processor_worker(container)
        await worker.run()
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
