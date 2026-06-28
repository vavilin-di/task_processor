from typing import Protocol, override

from sqlalchemy import ColumnElement, Select, and_, select, update
from sqlalchemy.orm import Mapped

from .sqlalchemy_repository import SQLAlchemyRepository


class IDisableable(Protocol):
    id: Mapped[int]
    is_active: Mapped[bool]


class SoftDeleteSQLAlchemyRepository[ModelT: IDisableable](SQLAlchemyRepository[ModelT]):
    @override
    async def delete(self, record_id: int) -> None:
        soft_delete_statement = update(self._model).where(self._model.id == record_id).values(is_active=False)
        await self._session.execute(soft_delete_statement)

    @override
    def _get_base_record_filter(self, record_id: int) -> ColumnElement[bool]:
        return and_(self._model.id == record_id, self._model.is_active)

    @override
    def _get_base_get_all_select_statement(self) -> Select[tuple[ModelT]]:
        return select(self._model).where(self._model.is_active).order_by(self._model.id)
