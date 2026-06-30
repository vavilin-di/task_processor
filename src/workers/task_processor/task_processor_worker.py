__all__ = ["get_task_processor_worker"]

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from dishka import AsyncContainer
from faststream.rabbit import RabbitBroker

from src.messaging.queues import TASKS_QUEUE
from src.services.tasks import TaskService

from ..utilities import use_broker

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from faststream._internal.endpoint.call_wrapper import HandlerCallWrapper

logger = logging.getLogger(__name__)


class TaskProcessorWorker:
    """Воркер для обработки задач из очереди task_processing.

    Получает сообщения из RabbitMQ, находит задачу по aggregate_id,
    выполняет её через TaskService и обновляет статус.
    """

    def __init__(self, broker: RabbitBroker, container: AsyncContainer) -> None:
        self._broker = broker
        self._container = container
        self._subscriber: HandlerCallWrapper[[dict[Any, Any]], Coroutine[Any, Any, None]] | None = None

    async def run(self) -> None:
        """Запускает воркер: подключается к брокеру и регистрирует подписчика."""
        async with use_broker(self._broker, logger):
            self._register_subscriber()
            logger.info(f"TaskProcessorWorker запущен и ожидает сообщения из очереди {TASKS_QUEUE.name}")
            await asyncio.get_running_loop().create_future()

    def _register_subscriber(self) -> None:
        """Регистрирует обработчик сообщений из очереди task_processing."""
        self._subscriber = self._broker.subscriber(TASKS_QUEUE)(self._handle_task_message)

    async def _handle_task_message(self, raw_message: dict) -> None:
        """Обрабатывает сообщение из очереди: обновляет статус задачи через TaskService."""
        aggregate_id: int | None = raw_message.get("aggregate_id")
        if aggregate_id is None:
            logger.warning(f"Получено сообщение без aggregate_id: {raw_message}")
            return

        logger.info(f"Начало обработки задачи с id={aggregate_id}")

        async with self._container() as request_container:
            task_service = await request_container.get(TaskService)

            try:
                task = await task_service.process_task(aggregate_id)
                if task is None:
                    logger.warning(f"Задача с id={aggregate_id} не найдена или неактивна")
            except Exception:
                logger.exception(f"Ошибка при обработке задачи с id={aggregate_id}")
                await task_service.fail_task(aggregate_id)


async def get_task_processor_worker(container: AsyncContainer) -> TaskProcessorWorker:
    """Фабрика для создания TaskProcessorWorker."""
    broker = await container.get(RabbitBroker)
    return TaskProcessorWorker(broker, container)
