from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workers.outbox_cleanup.outbox_cleanup_worker import run_outbox_cleanup_worker

pytestmark = pytest.mark.unit


class TestRunOutboxCleanupWorker:
    """Unit tests for run_outbox_cleanup_worker."""

    async def test_cleanup_deletes_messages(self) -> None:
        """Cleanup deletes expired messages and logs."""
        mock_container = MagicMock()
        request_container = MagicMock()
        mock_container.return_value = request_container
        request_container.__aenter__ = AsyncMock(return_value=request_container)
        request_container.__aexit__ = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.OUTBOX_TTL_HRS = 24
        mock_settings.OUTBOX_CLEANUP_BATCH_SIZE = 100
        mock_settings.OUTBOX_CLEANUP_INTERVAL_SEC = 60

        mock_cleanup_service = AsyncMock()
        mock_cleanup_service.cleanup.return_value = 42

        async def get_side_effect(cls: object) -> object:
            name = getattr(cls, "__name__", str(cls))
            if "Settings" in name:
                return mock_settings
            if "OutboxCleanupService" in name:
                return mock_cleanup_service
            msg = f"Unexpected class: {cls}"
            raise ValueError(msg)

        mock_container.get = get_side_effect
        request_container.get = get_side_effect

        with patch("src.workers.outbox_cleanup.outbox_cleanup_worker.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt]

            with pytest.raises(KeyboardInterrupt):
                await run_outbox_cleanup_worker(mock_container)

        mock_cleanup_service.cleanup.assert_awaited()

    async def test_cleanup_no_messages_to_delete(self) -> None:
        """Cleanup with no expired messages."""
        mock_container = MagicMock()
        request_container = MagicMock()
        mock_container.return_value = request_container
        request_container.__aenter__ = AsyncMock(return_value=request_container)
        request_container.__aexit__ = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.OUTBOX_TTL_HRS = 24
        mock_settings.OUTBOX_CLEANUP_BATCH_SIZE = 100
        mock_settings.OUTBOX_CLEANUP_INTERVAL_SEC = 60

        mock_cleanup_service = AsyncMock()
        mock_cleanup_service.cleanup.return_value = 0

        async def get_side_effect(cls: object) -> object:
            name = getattr(cls, "__name__", str(cls))
            if "Settings" in name:
                return mock_settings
            if "OutboxCleanupService" in name:
                return mock_cleanup_service
            msg = f"Unexpected class: {cls}"
            raise ValueError(msg)

        mock_container.get = get_side_effect
        request_container.get = get_side_effect

        with patch("src.workers.outbox_cleanup.outbox_cleanup_worker.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt]

            with pytest.raises(KeyboardInterrupt):
                await run_outbox_cleanup_worker(mock_container)

        mock_cleanup_service.cleanup.assert_awaited()
