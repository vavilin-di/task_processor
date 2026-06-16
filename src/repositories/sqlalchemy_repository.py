from itertools import chain
from typing import Any, Protocol

from sqlakeyset.asyncio import select_page
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Mapped
from sqlalchemy.sql.functions import GenericFunction


class IDisableable(Protocol):
    id: Mapped[int]
    is_active: Mapped[bool]


class SQLAlchemyRepository[ModelT: IDisableable]:
    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def create(self, **kwargs: dict[str, Any]) -> ModelT:
        object_from_db = self._model(**kwargs)
        self._session.add(object_from_db)
        await self._session.flush()
        await self._session.refresh(object_from_db)
        return object_from_db

    async def get(self, record_id: int) -> ModelT | None:
        select_statement = select(self._model).where(self._model.id == record_id, self._model.is_active)
        return (await self._session.execute(select_statement)).scalar_one_or_none()

    async def get_all(
        self, cursor: str | None, limit: int, filters: dict[str, Any] | None
    ) -> tuple[list[ModelT], str, bool]:
        select_statement = select(self._model).where(self._model.is_active)
        if filters is not None:
            select_statement = select_statement.where(
                and_(
                    *(
                        getattr(self._model, filter_field_name) == filter_field_value
                        for filter_field_name, filter_field_value in filters.items()
                    ),
                ),
            )
        page = await select_page(self._session, select_statement, limit, page=cursor)
        return list(chain.from_iterable(page)), page.paging.bookmark_next, page.paging.has_next

    async def get_value[FieldT](
        self, record_id: int, field: InstrumentedAttribute[FieldT] | GenericFunction[FieldT]
    ) -> FieldT | None:
        stmt = select(field).where(
            self._model.id == record_id,
            self._model.is_active,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update(self, record_id: int, **kwargs: object) -> ModelT | None:
        object_from_db = await self.get(record_id)
        if object_from_db is None:
            return None
        update_statement = update(self._model).where(self._model.id == record_id).values(**kwargs)
        await self._session.execute(update_statement)
        await self._session.flush()
        return await self.get(record_id)

    async def delete(self, record_id: int) -> None:
        update_statement = update(self._model).where(self._model.id == record_id).values(is_active=False)
        await self._session.execute(update_statement)
