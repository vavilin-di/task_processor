from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.di import (
    BrokerProvider,
    DatabaseProvider,
    RepositoryProvider,
    ServiceProvider,
    SettingsProvider,
    create_di_container,
)

pytestmark = pytest.mark.unit


class TestDatabaseProvider:
    """Unit-тесты для DatabaseProvider."""

    def test_get_engine(self) -> None:
        settings = MagicMock()
        settings.postgres.DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/db"

        with patch("src.di.create_async_engine") as mock_create_engine:
            provider = DatabaseProvider()
            engine = provider.get_engine(settings)

        mock_create_engine.assert_called_once()
        assert engine == mock_create_engine.return_value  # noqa: S101

    def test_get_session_factory(self) -> None:
        engine = MagicMock()

        with patch("src.di.async_sessionmaker") as mock_sessionmaker:
            provider = DatabaseProvider()
            factory = provider.get_session_factory(engine)

        mock_sessionmaker.assert_called_once_with(engine, class_=AsyncSession, expire_on_commit=False)
        assert factory == mock_sessionmaker.return_value  # noqa: S101

    async def test_get_session(self) -> None:
        session_factory = MagicMock()
        session = AsyncMock()
        session_factory.return_value.__aenter__.return_value = session

        provider = DatabaseProvider()
        async for sess in provider.get_session(session_factory):
            assert sess == session  # noqa: S101


class TestRepositoryProvider:
    """Unit-тесты для RepositoryProvider."""

    def test_get_task_repository(self) -> None:
        session = MagicMock()
        with patch("src.di.TaskRepository") as mock_repo:
            provider = RepositoryProvider()
            repo = provider.get_task_repository(session)

        mock_repo.assert_called_once()
        assert repo == mock_repo.return_value  # noqa: S101

    def test_get_outbox_message_repository(self) -> None:
        session = MagicMock()
        with patch("src.di.OutboxMessageRepository") as mock_repo:
            provider = RepositoryProvider()
            repo = provider.get_outbox_message_repository(session)

        mock_repo.assert_called_once()
        assert repo == mock_repo.return_value  # noqa: S101

    def test_get_dlq_message_repository(self) -> None:
        session = MagicMock()
        with patch("src.di.DLQMessageRepository") as mock_repo:
            provider = RepositoryProvider()
            repo = provider.get_dlq_message_repository(session)

        mock_repo.assert_called_once()
        assert repo == mock_repo.return_value  # noqa: S101


class TestServiceProvider:
    """Unit-тесты для ServiceProvider."""

    def test_get_task_service(self) -> None:
        task_repo = MagicMock()
        outbox_repo = MagicMock()
        session = MagicMock()

        with patch("src.di.TaskService") as mock_service:
            provider = ServiceProvider()
            service = provider.get_task_service(task_repo, outbox_repo, session)

        mock_service.assert_called_once_with(task_repo, outbox_repo, session)
        assert service == mock_service.return_value  # noqa: S101

    def test_get_outbox_message_service(self) -> None:
        broker = MagicMock()
        outbox_repo = MagicMock()
        session = MagicMock()

        with patch("src.di.OutboxMessageService") as mock_service:
            provider = ServiceProvider()
            service = provider.get_outbox_message_service(broker, outbox_repo, session)

        mock_service.assert_called_once_with(outbox_repo, broker, session)
        assert service == mock_service.return_value  # noqa: S101

    def test_get_outbox_cleanup_service(self) -> None:
        outbox_repo = MagicMock()
        session = MagicMock()

        with patch("src.di.OutboxCleanupService") as mock_service:
            provider = ServiceProvider()
            service = provider.get_outbox_cleanup_service(outbox_repo, session)

        mock_service.assert_called_once_with(outbox_repo, session)
        assert service == mock_service.return_value  # noqa: S101


class TestBrokerProvider:
    """Unit-тесты для BrokerProvider."""

    def test_get_broker_with_rabbit_settings(self) -> None:
        settings = MagicMock()
        settings.rabbit_mq = MagicMock()
        settings.rabbit_mq.DATABASE_URL = "amqp://guest:guest@localhost:5672/"

        with patch("src.di.RabbitBroker") as mock_broker:
            provider = BrokerProvider()
            broker = provider.get_broker(settings)

        mock_broker.assert_called_once_with("amqp://guest:guest@localhost:5672/")
        assert broker == mock_broker.return_value  # noqa: S101

    def test_get_broker_without_rabbit_settings(self) -> None:
        settings = MagicMock()
        settings.rabbit_mq = None

        with patch("src.di.RabbitBroker") as mock_broker, patch("src.di.RabbitMQSettings") as mock_rabbit_settings:
            mock_rabbit_settings.return_value.DATABASE_URL = "amqp://guest:guest@localhost:5672/"
            provider = BrokerProvider()
            broker = provider.get_broker(settings)

        mock_broker.assert_called_once_with("amqp://guest:guest@localhost:5672/")
        assert broker == mock_broker.return_value  # noqa: S101


class TestSettingsProvider:
    """Unit-тесты для SettingsProvider."""

    def test_get_settings(self) -> None:
        with patch("src.di.get_settings") as mock_get_settings:
            provider = SettingsProvider()
            settings = provider.get_settings()

        mock_get_settings.assert_called_once()
        assert settings == mock_get_settings.return_value  # noqa: S101


class TestCreateDIContainer:
    """Unit-тесты для create_di_container."""

    def test_create_di_container(self) -> None:
        with patch("src.di.make_async_container") as mock_container:
            result = create_di_container()

        mock_container.assert_called_once()
        assert result == mock_container.return_value  # noqa: S101
