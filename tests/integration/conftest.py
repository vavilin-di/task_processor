from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from faststream.rabbit import RabbitBroker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.di import RepositoryProvider, ServiceProvider, SettingsProvider
from src.routers import tasks_router
from src.settings import get_settings


class TestSessionProvider(Provider):
    """Провайдер, создающий свежую сессию на каждый запрос из общего engine."""

    def __init__(self, engine: AsyncEngine) -> None:
        super().__init__()
        self._engine = engine

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Создаёт новую сессию с отдельным соединением.

        Транзакция управляется через session.begin() в сервисах.
        После завершения запроса соединение автоматически закрывается.
        """
        connection = await self._engine.connect()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await connection.close()


class TestBrokerProvider(Provider):
    """Провайдер, возвращающий замоканный RabbitBroker."""

    @provide(scope=Scope.APP)
    def get_broker(self) -> RabbitBroker:
        return AsyncMock(spec=RabbitBroker)  # type: ignore[return-value]


@pytest_asyncio.fixture(scope="function")
async def session(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Свежая транзакция на каждый тест с откатом после завершения.

    Используется тестами, которые работают с репозиторием напрямую (не через Dishka).
    """
    connection = await pg_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function")
async def di_container(pg_engine: AsyncEngine) -> AsyncContainer:
    """DI-контейнер с PostgreSQL сессией для integration-тестов.

    Использует общий pg_engine из корневого conftest.py (SharedPostgresContainer).
    Сессия создаётся через TestSessionProvider с отдельным соединением и транзакцией.
    """
    return make_async_container(
        SettingsProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        TestSessionProvider(pg_engine),
        TestBrokerProvider(),
    )


@pytest_asyncio.fixture(scope="function")
async def app(di_container: AsyncContainer) -> FastAPI:
    """Fresh FastAPI app с тестовым DI-контейнером."""
    settings = get_settings()
    app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION)

    base_router = APIRouter(prefix=settings.API_PREFIX)
    version_router = APIRouter(prefix=settings.API_VERSION_PREFIX)
    version_router.include_router(tasks_router)
    base_router.include_router(version_router)
    app.include_router(base_router)

    setup_dishka(container=di_container, app=app)
    return app


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """TestClient для HTTP-тестов."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac
