import operator
from itertools import chain
from typing import Any, Protocol

from sqlakeyset.asyncio import select_page
from sqlalchemy import Select, and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Mapped
from sqlalchemy.sql.functions import GenericFunction


class IDisableable(Protocol):
    id: Mapped[int]
    is_active: Mapped[bool]


_FILTER_OPERATORS: tuple[tuple[str, Any], ...] = (("_from", operator.ge), ("_to", operator.le))


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

    async def exists(self, record_id: int) -> bool:
        exists_statement = select(
            select(self._model).where(self._model.id == record_id, self._model.is_active).exists()
        )
        return bool((await self._session.execute(exists_statement)).scalar())

    async def get_all(
        self, cursor: str | None, limit: int, filters: dict[str, Any] | None
    ) -> tuple[list[ModelT], str, bool]:
        select_statement = select(self._model).where(self._model.is_active)
        if filters is not None:
            select_statement = self._get_filtered_statement(select_statement, filters)
        page = await select_page(self._session, select_statement, limit, page=cursor)
        return list(chain.from_iterable(page)), page.paging.bookmark_next, page.paging.has_next

    def _get_filtered_statement(
        self, select_statement: Select[tuple[ModelT]], filters: dict[str, Any]
    ) -> Select[tuple[ModelT]]:
        conditions = []
        for filter_field_name, filter_field_value in filters.items():
            if filter_field_value is None:
                continue

            for filter_suffix, filter_operator in _FILTER_OPERATORS:
                if not filter_field_name.endswith(filter_suffix):
                    continue
                field_name = filter_field_name[: -len(filter_suffix)]
                field = getattr(self._model, field_name, None)
                operation = filter_operator
                break
            else:
                operation = operator.eq
                field = getattr(self._model, filter_field_name, None)

            if field is not None and isinstance(field, InstrumentedAttribute):
                conditions.append(operation(field, filter_field_value))
        return select_statement.where(and_(*conditions)) if conditions else select_statement

    async def get_value[FieldT](
        self, record_id: int, field: InstrumentedAttribute[FieldT] | GenericFunction[FieldT]
    ) -> FieldT | None:
        stmt = select(field).where(
            self._model.id == record_id,
            self._model.is_active,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def update(self, record_id: int, **kwargs: object) -> ModelT | None:
        is_object_exist = await self.exists(record_id)
        if not is_object_exist:
            return None
        update_statement = (
            update(self._model).where(self._model.id == record_id).values(**kwargs).returning(self._model)
        )
        update_result = await self._session.execute(update_statement)
        await self._session.flush()
        return update_result.scalar_one_or_none()

    async def delete(self, record_id: int) -> None:
        update_statement = update(self._model).where(self._model.id == record_id).values(is_active=False)
        await self._session.execute(update_statement)
