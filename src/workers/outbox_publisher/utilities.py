from asyncio import CancelledError
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger

from faststream.rabbit import RabbitBroker


@asynccontextmanager
async def use_broker(broker: RabbitBroker, logger: Logger) -> AsyncGenerator[None, None]:
    exception_type: BaseException | None = None
    broker_repr = repr(broker)
    try:
        await broker.start()
        logger.info(f"Брокер {broker_repr} запущен")
        yield
    except CancelledError as ex:
        logger.info(f"Брокер {broker_repr} остановлен")
        exception_type = ex
    except Exception as ex:
        logger.error(f"Во время работы брокера {broker_repr} произошла ошибка: {ex}")
        exception_type = ex
    finally:
        if exception_type is None:
            await broker.stop()
        else:
            await broker.stop(type(exception_type), exception_type, exception_type.__traceback__)
