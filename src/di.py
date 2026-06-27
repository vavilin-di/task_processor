from collections.abc import AsyncIterable

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from faststream.rabbit import RabbitBroker
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.database.models.dlq_messages import DLQMessage
from src.database.models.outbox_messages import OutboxMessage
from src.database.models.tasks import Task
from src.repositories.dlq_messages import DLQMessageRepository
from src.repositories.outbox_messages import OutboxMessageRepository
from src.repositories.tasks import TaskRepository
from src.services.outbox_messages import OutboxMessageService
from src.services.tasks import TaskService
from src.settings import Settings, get_settings


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_engine(self, settings: Settings) -> AsyncEngine:
        database_url = make_url(settings.postgres.DATABASE_URL).set(drivername="postgresql+asyncpg")
        return create_async_engine(database_url)

    @provide(scope=Scope.APP)
    def get_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(self, session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_task_repository(self, session: AsyncSession) -> TaskRepository:
        return TaskRepository(Task, session)

    @provide(scope=Scope.REQUEST)
    def get_outbox_message_repository(self, session: AsyncSession) -> OutboxMessageRepository:
        return OutboxMessageRepository(OutboxMessage, session)

    @provide(scope=Scope.REQUEST)
    def get_dlq_message_repository(self, session: AsyncSession) -> DLQMessageRepository:
        return DLQMessageRepository(DLQMessage, session)


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_task_service(
        self, task_repository: TaskRepository, outbox_repository: OutboxMessageRepository, session: AsyncSession
    ) -> TaskService:
        return TaskService(task_repository, outbox_repository, session)

    @provide(scope=Scope.REQUEST)
    def get_outbox_message_service(
        self, broker: RabbitBroker, outbox_repository: OutboxMessageRepository, session: AsyncSession
    ) -> OutboxMessageService:
        return OutboxMessageService(outbox_repository, broker, session)


class BrokerProvider(Provider):
    @provide(scope=Scope.APP)
    def get_broker(self, settings: Settings) -> RabbitBroker:
        return RabbitBroker(settings.rabbit_mq.DATABASE_URL)


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return get_settings()


def create_di_container() -> AsyncContainer:
    return make_async_container(
        SettingsProvider(), BrokerProvider(), DatabaseProvider(), RepositoryProvider(), ServiceProvider()
    )
