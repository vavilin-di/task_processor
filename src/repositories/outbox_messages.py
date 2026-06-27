from typing import Any

from sqlalchemy import not_, select, update

from src.database.models.outbox_messages import OutboxMessage as OutboxMessage

from .sqlalchemy_repository import SQLAlchemyRepository

MAX_PUBLISH_ERRORS_COUNT = 5


class OutboxMessageRepository(SQLAlchemyRepository[OutboxMessage]):
    async def get_not_published_outbox_messages(self, limit: int = 10) -> list[tuple[int, str, dict[str, Any]]]:
        statement = (
            select(OutboxMessage.id, OutboxMessage.routing_key, OutboxMessage.payload)
            .where(not_(OutboxMessage.is_published), not_(OutboxMessage.is_failed))
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(statement)).t.all())

    async def mark_task_as_published(self, task_id: int) -> None:
        await self.update(task_id, is_published=True)

    async def add_error(self, task_id: int, error: str) -> None:
        returning_update_statement = (
            update(OutboxMessage)
            .where(OutboxMessage.id == task_id)
            .values(errors=[*OutboxMessage.errors, error])
            .returning(OutboxMessage.errors)
        )
        result = await self._session.execute(returning_update_statement)
        updated_errors = result.scalar_one_or_none()
        if updated_errors is None:
            raise AssertionError(f"OutboxMessage с id={task_id} не найдено")
        if len(updated_errors) >= MAX_PUBLISH_ERRORS_COUNT:
            await self._session.execute(update(OutboxMessage).where(OutboxMessage.id == task_id).values(is_failed=True))
