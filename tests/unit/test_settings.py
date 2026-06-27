import pytest
from pydantic import SecretStr

from src.settings.postgres import PostgresSettings
from src.settings.rabbit_mq import RabbitMQSettings


class TestPostgresSettings:
    """Тесты для PostgresSettings."""

    def test_build_database_url(self) -> None:
        settings = PostgresSettings(
            HOST="localhost",
            PORT=5432,
            USER="test_user",
            PASSWORD=SecretStr("test_pass"),
            DATABASE="test_db",
            POOL_SIZE=5,
            MAX_OVERFLOW=10,
            POOL_TIMEOUT=30,
            POOL_RECYCLE=1800,
        )
        assert "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db" in settings.DATABASE_URL  # noqa: S101


class TestRabbitMQSettings:
    """Тесты для RabbitMQSettings."""

    def test_build_database_url(self) -> None:
        settings = RabbitMQSettings(
            HOST="localhost",
            PORT=5672,
            USER="guest",
            PASSWORD=SecretStr("guest"),
            VIRTUAL_HOST="/",
            PREFETCH_COUNT=10,
            HEARTBEAT=60,
        )
        assert "amqp://guest:guest@localhost:5672/" in settings.DATABASE_URL  # noqa: S101
