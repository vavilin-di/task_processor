from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from faststream.rabbit import RabbitBroker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.database.models.base import Base
from src.di import DatabaseProvider, RepositoryProvider, ServiceProvider, SettingsProvider
from src.routers import tasks_router
from src.settings import get_settings


class TestE2ESessionProvider(Provider):
    """Провайдер, переопределяющий сессию на SQLite in-memory для e2e-тестов."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncSession:
        return self._session


class TestE2EBrokerProvider(Provider):
    """Провайдер, возвращающий замоканный RabbitBroker для e2e-тестов."""

    @provide(scope=Scope.APP)
    def get_broker(self) -> RabbitBroker:
        return AsyncMock(spec=RabbitBroker)  # type: ignore[return-value]


@pytest_asyncio.fixture(scope="session")
async def e2e_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine для e2e-тестов (создание таблиц один раз на сессию)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def e2e_session(e2e_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Свежая транзакция на каждый e2e-тест с откатом после завершения."""
    connection = await e2e_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function")
async def e2e_di_container(e2e_session: AsyncSession) -> AsyncContainer:
    """DI-контейнер с SQLite in-memory сессией для e2e-тестов."""
    return make_async_container(
        SettingsProvider(),
        DatabaseProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        TestE2ESessionProvider(e2e_session),
        TestE2EBrokerProvider(),
    )


@pytest_asyncio.fixture(scope="function")
async def e2e_app(e2e_di_container: AsyncContainer) -> FastAPI:
    """Fresh FastAPI app с тестовым DI-контейнером для e2e-тестов."""
    settings = get_settings()
    app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

    base_router = APIRouter(prefix=settings.API_PREFIX)
    version_router = APIRouter(prefix=settings.API_VERSION_PREFIX)
    version_router.include_router(tasks_router)
    base_router.include_router(version_router)
    app.include_router(base_router)

    setup_dishka(container=e2e_di_container, app=app)
    return app


@pytest_asyncio.fixture(scope="function")
async def client(e2e_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """TestClient для e2e-тестов."""
    transport = ASGITransport(app=e2e_app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
