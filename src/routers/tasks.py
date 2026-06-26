from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
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

DEFAULT_TASKS_LIST_LIMIT = 20

task_list_adapter = TypeAdapter(list[TaskSchema])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

ROUTING_KEY = "tasks.create"


@tasks_router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
@inject
async def create_task(
    session: FromDishka[AsyncSession],
    tasks_repo: FromDishka[TaskRepository],
    outbox_messages_repo: FromDishka[OutboxMessageRepository],
    task: TaskCreate,
) -> TaskModel:
    async with session.begin():
        task_model = await tasks_repo.create(**task.model_dump())
        # TODO: уточнить происхождение, содержимое и формат (?) payload
        outbox_message = OutboxMessageCreate(
            routing_key=ROUTING_KEY, aggregate_id=task_model.id, payload=task_model.payload
        )
        await outbox_messages_repo.create(**outbox_message.model_dump())
        return task_model


@tasks_router.get("", response_model=PaginatedResponse[TaskSchema], status_code=status.HTTP_200_OK)
@inject
async def get_tasks(
    repo: FromDishka[TaskRepository],
    cursor: str | None = None,
    limit: int = DEFAULT_TASKS_LIST_LIMIT,
    filter_: Annotated[TaskFilter, Depends()] | None = None,
) -> PaginatedResponse[TaskSchema]:
    items, next_cursor, has_next = await repo.get_all(
        cursor,
        limit,
        None if filter_ is None else filter_.model_dump(exclude_none=True),
    )
    validated_items = task_list_adapter.validate_python(items)
    return PaginatedResponse(items=validated_items, next_cursor=next_cursor, has_next=has_next)


@tasks_router.get("/{task_id}", response_model=TaskSchema, status_code=status.HTTP_200_OK)
@inject
async def get_task(task_id: int, repo: FromDishka[TaskRepository]) -> TaskModel | None:
    task = await repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@tasks_router.delete("/{task_id}", response_model=TaskSchema, status_code=status.HTTP_200_OK)
@inject
async def cancel_task(task_id: int, repo: FromDishka[TaskRepository], session: FromDishka[AsyncSession]) -> TaskModel:
    task = await repo.cancel_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@tasks_router.get("/{task_id}/status")
@inject
async def get_task_status(task_id: int, repo: FromDishka[TaskRepository]) -> TaskStatus:
    task_status = await repo.get_task_status(task_id)
    if task_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task_status
