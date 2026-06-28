from collections.abc import AsyncGenerator
from os import getenv

import pytest
import pytest_asyncio
from dishka import AsyncContainer, make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.database.models.base import Base
from src.di import RepositoryProvider, SettingsProvider
from src.settings.postgres import PostgresSettings


class SharedPostgresContainer:
    """Singleton-обёртка для PostgreSQL testcontainer.

    Позволяет использовать один контейнер для всех тестов (integration + e2e),
    избегая конфликта портов при запуске нескольких контейнеров.

    Контейнер (Docker) запускается один раз на сессию.
    URL базы данных сохраняется, но engine создаётся per-function,
    чтобы избежать привязки пула соединений к конкретному event loop.
    """

    _container: PostgresContainer | None = None
    _database_url: str | None = None

    @classmethod
    def get_url(cls) -> str:
        """Возвращает URL подключения к БД.

        Если контейнер ещё не запущен — запускает его.
        """
        if cls._database_url is not None:
            return cls._database_url

        if getenv("CI"):
            settings = PostgresSettings()
            cls._database_url = settings.DATABASE_URL
            return cls._database_url

        cls._container = PostgresContainer("postgres:14.5")
        cls._container.start()
        cls._database_url = cls._container.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")
        return cls._database_url

    @classmethod
    async def create_tables(cls) -> None:
        """Создаёт схему БД через временный engine."""
        engine = create_async_engine(cls.get_url(), echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    @classmethod
    async def drop_tables(cls) -> None:
        """Удаляет схему БД через временный engine."""
        engine = create_async_engine(cls.get_url(), echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @classmethod
    def stop(cls) -> None:
        """Останавливает Docker-контейнер."""
        if cls._container is not None:
            cls._container.stop()
            cls._container = None
        cls._database_url = None


@pytest_asyncio.fixture(scope="function")
async def pg_engine() -> AsyncGenerator[AsyncEngine, None]:
    """PostgreSQL engine из общего testcontainer.

    Engine создаётся per-function, чтобы избежать привязки пула соединений
    к конкретному event loop. Контейнер (Docker) запускается один раз.
    """
    # Запускаем контейнер при первом вызове
    url = SharedPostgresContainer.get_url()

    # Создаём таблицы при первом вызове
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Свежая транзакция на каждый тест с откатом после завершения."""
    connection = await pg_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function")
async def container() -> AsyncGenerator[AsyncContainer, None]:
    """DI-контейнер без DatabaseProvider (только настройки и репозитории).

    DatabaseProvider исключён, т.к. он создаёт реальное подключение к PostgreSQL
    через asyncpg. Unit-тесты используют моки, а integration/e2e тесты
    имеют свои conftest с testcontainer.
    """
    container = make_async_container(
        SettingsProvider(),
        RepositoryProvider(),
    )
    yield container
    await container.close()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Останавливает Docker-контейнер после завершения тестовой сессии."""
    SharedPostgresContainer.stop()
