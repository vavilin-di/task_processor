from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI
from faststream.rabbit import RabbitBroker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.di import BrokerProvider, DatabaseProvider, RepositoryProvider, ServiceProvider, SettingsProvider
from src.routers import tasks_router
from src.settings import get_settings


class TestSessionProvider(Provider):
    """Провайдер, переопределяющий сессию на тестовую (SQLite in-memory)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncSession:
        return self._session


class TestBrokerProvider(Provider):
    """Провайдер, возвращающий замоканный RabbitBroker."""

    @provide(scope=Scope.APP)
    def get_broker(self) -> RabbitBroker:
        return AsyncMock(spec=RabbitBroker)  # type: ignore[return-value]


@pytest_asyncio.fixture(scope="function")
async def di_container(session: AsyncSession) -> AsyncContainer:
    """DI-контейнер с SQLite in-memory сессией для integration-тестов."""
    return make_async_container(
        SettingsProvider(),
        DatabaseProvider(),
        RepositoryProvider(),
        ServiceProvider(),
        TestSessionProvider(session),
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
