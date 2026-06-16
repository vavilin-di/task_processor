from sqlalchemy import not_, select
from sqlalchemy.sql.functions import count

from src.database.models.outbox_messages import OutboxMessage

from .sqlalchemy_repository import SQLAlchemyRepository

MAX_PUBLISH_ERRORS_COUNT = 5


class OutboxMessageRepository(SQLAlchemyRepository[OutboxMessage]):
    async def get_not_published_task_ids(self, limit: int = 10) -> list[tuple[int, str]]:
        statement = (
            select(OutboxMessage.id, OutboxMessage.routing_key)
            .where(not_(OutboxMessage.is_published), not_(OutboxMessage.is_failed))
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(statement)).t.all())

    async def mark_task_as_published(self, task_id: int) -> None:
        await self.update(task_id, **{str(OutboxMessage.is_published): True})

    async def add_error(self, task_id: int, error: str) -> None:
        errors_count = await self.get_value(task_id, count(OutboxMessage.errors))
        if errors_count is None:
            raise AssertionError(f"errors_count is None для задачи с id={task_id}")
        if errors_count >= MAX_PUBLISH_ERRORS_COUNT:
            await self.update(task_id, **{str(OutboxMessage.is_failed): True})
            return
        await self.update(task_id, **{str(OutboxMessage.errors): OutboxMessage.errors.concat(error)})
