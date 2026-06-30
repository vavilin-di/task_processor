import asyncio

from src.di import create_di_container
from src.workers.outbox_cleanup.outbox_cleanup_worker import run_outbox_cleanup_worker


async def main():
    container = create_di_container()
    try:
        await run_outbox_cleanup_worker(container)
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
