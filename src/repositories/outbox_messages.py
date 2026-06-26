from sqlalchemy import not_, select

from src.database.models.outbox_messages import OutboxMessage as OutboxMessageModel
from src.schemas.outbox_messages import OutboxMessage

from .sqlalchemy_repository import SQLAlchemyRepository

MAX_PUBLISH_ERRORS_COUNT = 5


class OutboxMessageRepository(SQLAlchemyRepository[OutboxMessageModel]):

    async def get_not_published_tasks(self, limit: int = 10) -> list[OutboxMessage]:
        statement = (
            select(OutboxMessageModel.id, OutboxMessageModel.routing_key, OutboxMessageModel.payload)
            .where(not_(OutboxMessageModel.is_published), not_(OutboxMessageModel.is_failed))
            .order_by(OutboxMessageModel.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [
            OutboxMessage(id=id, routing_key=routing_key, payload=payload)
            for id, routing_key, payload in (await self._session.execute(statement)).t.all()
        ]

    async def mark_task_as_published(self, task_id: int) -> None:
        await self.update(task_id, is_published=True)

    async def add_error(self, task_id: int, error: str) -> None:
        message = await self.get(task_id)
        if message is None:
            raise AssertionError(f"OutboxMessage с id={task_id} не найдено")
        message.errors.append(error)
        if len(message.errors) >= MAX_PUBLISH_ERRORS_COUNT:
            await self.update(task_id, errors=message.errors, is_failed=True)
            return
        await self.update(task_id, errors=message.errors)
