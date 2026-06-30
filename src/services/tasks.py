import asyncio
import logging
from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.tasks import Task as TaskModel
from src.enums import TaskStatus
from src.repositories.outbox_messages import OutboxMessageRepository
from src.repositories.tasks import TaskRepository
from src.schemas.common import PaginatedResponse
from src.schemas.outbox_messages import OutboxMessageCreate
from src.schemas.tasks import Task as TaskSchema
from src.schemas.tasks import TaskCreate, TaskFilter

ROUTING_KEY = "tasks.create"
DEFAULT_TASKS_LIST_LIMIT = 20
TASK_PROCESSING_DELAY_SEC = 2

logger = logging.getLogger(__name__)
task_list_adapter = TypeAdapter(list[TaskSchema])


class TaskService:
    def __init__(
        self, task_repository: TaskRepository, outbox_repository: OutboxMessageRepository, session: AsyncSession
    ) -> None:
        self._tasks_repository = task_repository
        self._outbox_repository = outbox_repository
        self._session = session

    async def create_task(self, task: TaskCreate) -> TaskModel:
        async with self._session.begin():
            task_model = await self._tasks_repository.create(**task.model_dump())
            outbox_message = OutboxMessageCreate(
                routing_key=ROUTING_KEY, aggregate_id=task_model.id, payload=task_model.payload
            )
            await self._outbox_repository.create(**outbox_message.model_dump())
            return task_model

    async def get_tasks(
        self, limit: int, cursor: str | None = None, filter_: TaskFilter | None = None
    ) -> PaginatedResponse[TaskSchema]:
        items, next_cursor, has_next = await self._tasks_repository.get_all(
            cursor,
            limit,
            None if filter_ is None else filter_.model_dump(exclude_none=True),
        )
        validated_items = task_list_adapter.validate_python(items)
        return PaginatedResponse(items=validated_items, next_cursor=next_cursor, has_next=has_next)

    async def get_task(self, task_id: int) -> TaskModel | None:
        return await self._tasks_repository.get(task_id)

    async def cancel_task(self, task_id: int) -> TaskModel | None:
        return await self._tasks_repository.cancel_task(task_id)

    async def get_task_status(self, task_id: int) -> TaskStatus | None:
        return await self._tasks_repository.get_task_status(task_id)

    async def process_task(self, task_id: int) -> TaskModel | None:
        now = datetime.now(UTC).replace(tzinfo=None)
        async with self._session.begin():
            task = await self._tasks_repository.update(
                record_id=task_id,
                status=TaskStatus.IN_PROGRESS,
                started_at=now,
            )
            if task is None:
                logger.warning(f"Задача с id={task_id} не найдена или неактивна")
                return None

        # Симуляция выполнения задачи
        await asyncio.sleep(TASK_PROCESSING_DELAY_SEC)

        async with self._session.begin():
            task = await self._tasks_repository.update(
                record_id=task_id,
                status=TaskStatus.COMPLETED,
                finished_at=datetime.now(UTC).replace(tzinfo=None),
                result={"message": "Задача успешно обработана"},
            )

        logger.info(f"Задача id={task_id} успешно обработана")
        return task

    async def fail_task(self, task_id: int, errors: list[str] | None = None) -> TaskModel | None:
        async with self._session.begin():
            return await self._tasks_repository.update(
                record_id=task_id,
                status=TaskStatus.FAILED,
                finished_at=datetime.now(UTC).replace(tzinfo=None),
                errors=["Внутренняя ошибка обработчика"] if errors is None else errors,
            )
