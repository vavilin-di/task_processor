from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import TypeAdapter

from src.database.models.tasks import Task as TaskModel
from src.enums import TaskStatus
from src.schemas.common import PaginatedResponse
from src.schemas.tasks import Task as TaskSchema
from src.schemas.tasks import TaskCreate, TaskFilter
from src.services.tasks import TaskService

DEFAULT_TASKS_LIST_LIMIT = 20

task_list_adapter = TypeAdapter(list[TaskSchema])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

ROUTING_KEY = "tasks.create"


@tasks_router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
@inject
async def create_task(service: FromDishka[TaskService], task: TaskCreate) -> TaskModel:
    return await service.create_task(task)


@tasks_router.get("", response_model=PaginatedResponse[TaskSchema], status_code=status.HTTP_200_OK)
@inject
async def get_tasks(
    service: FromDishka[TaskService],
    cursor: str | None = None,
    limit: int = DEFAULT_TASKS_LIST_LIMIT,
    filter_: Annotated[TaskFilter, Depends()] | None = None,
) -> PaginatedResponse[TaskSchema]:
    return await service.get_tasks(limit, cursor, filter_)


@tasks_router.get("/{task_id}", response_model=TaskSchema, status_code=status.HTTP_200_OK)
@inject
async def get_task(service: FromDishka[TaskService], task_id: int) -> TaskModel | None:
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@tasks_router.delete("/{task_id}", response_model=TaskSchema, status_code=status.HTTP_200_OK)
@inject
async def cancel_task(service: FromDishka[TaskService], task_id: int) -> TaskModel:
    task = await service.cancel_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@tasks_router.get("/{task_id}/status")
@inject
async def get_task_status(service: FromDishka[TaskService], task_id: int) -> TaskStatus:
    task_status = await service.get_task_status(task_id)
    if task_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task_status
