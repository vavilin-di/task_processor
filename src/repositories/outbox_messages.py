from collections.abc import AsyncGenerator, Iterable
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, not_, select, update
from sqlalchemy.sql import true

from src.database.models.outbox_messages import OutboxMessage as OutboxMessage

from .sqlalchemy_repository import SQLAlchemyRepository

MAX_PUBLISH_ERRORS_COUNT = 5


class OutboxMessageRepository(SQLAlchemyRepository[OutboxMessage]):
    async def get_not_published_outbox_messages(
        self, limit: int = 10
    ) -> AsyncGenerator[tuple[int, str, dict[Any, Any]], None]:
        statement = (
            select(OutboxMessage.id, OutboxMessage.routing_key, OutboxMessage.payload)
            .where(not_(OutboxMessage.is_published), not_(OutboxMessage.is_failed))
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .execution_options(stream_results=True, max_row_buffer=limit)
        )
        async for item in await self._session.stream(statement):
            yield item.tuple()

    async def mark_messages_as_published(self, message_ids: Iterable[int]) -> None:
        batch_update_statement = (
            update(OutboxMessage).where(OutboxMessage.id.in_(message_ids)).values(is_published=True)
        )
        await self._session.execute(batch_update_statement)

    async def add_error(self, task_id: int, error: str) -> None:
        returning_update_statement = (
            update(OutboxMessage)
            .where(OutboxMessage.id == task_id)
            .values(errors=func.array_append(OutboxMessage.errors, error))
            .returning(OutboxMessage.errors)
        )
        result = await self._session.execute(returning_update_statement)
        updated_errors = result.scalar_one_or_none()
        if updated_errors is None:
            raise AssertionError(f"OutboxMessage с id={task_id} не найдено")
        if len(updated_errors) >= MAX_PUBLISH_ERRORS_COUNT:
            await self._session.execute(update(OutboxMessage).where(OutboxMessage.id == task_id).values(is_failed=True))

    async def delete_published_older_than(self, ttl_hours: int, batch_size: int) -> int:
        timestamp_treshold = func.now() - timedelta(hours=ttl_hours)

        get_ids_to_delete_cte = (
            select(OutboxMessage.id)
            .where(OutboxMessage.is_published == true(), OutboxMessage.created_at < timestamp_treshold)
            .limit(batch_size)
            .cte("ids_to_delete")
        )

        get_deleted_ids_cte = (
            delete(OutboxMessage)
            .where(OutboxMessage.id.in_(select(get_ids_to_delete_cte.c.id)))
            .returning(OutboxMessage.id)
            .cte("deleted")
        )

        count_stmt = select(func.count()).select_from(get_deleted_ids_cte)
        result = await self._session.execute(count_stmt)
        return result.scalar_one()
