from src.database.models.tasks import Task
from src.enums import TaskStatus

from .soft_delete_sqlalchemy_repository import SoftDeleteSQLAlchemyRepository


class TaskRepository(SoftDeleteSQLAlchemyRepository[Task]):
    async def cancel_task(self, record_id: int) -> Task | None:
        return await self.update(record_id=record_id, status=TaskStatus.CANCELLED)

    async def get_task_status(self, record_id: int) -> TaskStatus | None:
        return await self.get_value(record_id, Task.status)
