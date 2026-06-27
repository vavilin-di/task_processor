from src.database.models.dlq_messages import DLQMessage as DLQMessageModel

from .sqlalchemy_repository import SQLAlchemyRepository


class DLQMessageRepository(SQLAlchemyRepository[DLQMessageModel]): ...
