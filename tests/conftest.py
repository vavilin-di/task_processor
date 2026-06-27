import asyncio
from asyncio.events import AbstractEventLoop
from collections.abc import AsyncGenerator, AsyncIterable, Generator
from typing import Any

import pytest
import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.database.models.base import Base
from src.di import DatabaseProvider, RepositoryProvider, SettingsProvider


class TestSessionProvider(Provider):
    """Провайдер, переопределяющий сессию на тестовую (SQLite in-memory)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncIterable[AsyncSession]:
        yield self._session


@pytest.fixture(scope="session")
def event_loop() -> Generator[AbstractEventLoop, Any, None]:
    """Один event_loop на сессию для всех async-тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine для тестов (создание таблиц один раз на сессию)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Свежая транзакция на каждый тест с откатом после завершения."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function")
async def container(session: AsyncSession) -> AsyncGenerator[AsyncContainer, None]:
    """DI-контейнер с переопределённой сессией (SQLite in-memory)."""
    container = make_async_container(
        SettingsProvider(),
        DatabaseProvider(),
        RepositoryProvider(),
        TestSessionProvider(session),
    )
    yield container
    await container.close()
