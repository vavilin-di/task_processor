from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestRunOutboxCleanupMain:
    """Unit tests for run_outbox_cleanup_worker.py main."""

    async def test_main_creates_container_and_runs_cleanup(self) -> None:
        """main creates DI container and runs cleanup worker."""
        with (
            patch("src.workers.outbox_cleanup.run_outbox_cleanup_worker.create_di_container") as mock_create,
            patch("src.workers.outbox_cleanup.run_outbox_cleanup_worker.run_outbox_cleanup_worker") as mock_run,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container

            from src.workers.outbox_cleanup.run_outbox_cleanup_worker import main

            await main()

        mock_create.assert_called_once()
        mock_run.assert_awaited_once_with(mock_container)
        mock_container.close.assert_awaited_once()

    async def test_main_closes_container_on_error(self) -> None:
        """main closes container even if worker raises an error."""
        with (
            patch("src.workers.outbox_cleanup.run_outbox_cleanup_worker.create_di_container") as mock_create,
            patch("src.workers.outbox_cleanup.run_outbox_cleanup_worker.run_outbox_cleanup_worker") as mock_run,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container
            mock_run.side_effect = RuntimeError("Worker error")

            from src.workers.outbox_cleanup.run_outbox_cleanup_worker import main

            with pytest.raises(RuntimeError, match="Worker error"):
                await main()

        mock_container.close.assert_awaited_once()


class TestRunTaskProcessorMain:
    """Unit tests for run_task_processor_worker.py main."""

    async def test_main_creates_container_and_runs_worker(self) -> None:
        """main creates DI container and runs task processor worker."""
        with (
            patch("src.workers.task_processor.run_task_processor_worker.create_di_container") as mock_create,
            patch("src.workers.task_processor.run_task_processor_worker.get_task_processor_worker") as mock_get,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container
            mock_worker = AsyncMock()
            mock_get.return_value = mock_worker

            from src.workers.task_processor.run_task_processor_worker import main

            await main()

        mock_create.assert_called_once()
        mock_get.assert_awaited_once_with(mock_container)
        mock_worker.run.assert_awaited_once()
        mock_container.close.assert_awaited_once()

    async def test_main_closes_container_on_error(self) -> None:
        """main closes container even if worker raises an error."""
        with (
            patch("src.workers.task_processor.run_task_processor_worker.create_di_container") as mock_create,
            patch("src.workers.task_processor.run_task_processor_worker.get_task_processor_worker") as mock_get,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container
            mock_worker = AsyncMock()
            mock_worker.run.side_effect = RuntimeError("Worker error")
            mock_get.return_value = mock_worker

            from src.workers.task_processor.run_task_processor_worker import main

            with pytest.raises(RuntimeError, match="Worker error"):
                await main()

        mock_container.close.assert_awaited_once()


class TestRunOutboxPublishMain:
    """Unit tests for run_outbox_publish_worker.py main."""

    async def test_main_creates_container_and_runs_publisher(self) -> None:
        """main creates DI container and runs outbox publish worker."""
        with (
            patch("src.workers.outbox_publisher.run_outbox_publish_worker.create_di_container") as mock_create,
            patch("src.workers.outbox_publisher.run_outbox_publish_worker.run_outbox_publish_worker") as mock_run,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container

            from src.workers.outbox_publisher.run_outbox_publish_worker import main

            await main()

        mock_create.assert_called_once()
        mock_run.assert_awaited_once_with(mock_container, poll_interval=0.5)
        mock_container.close.assert_awaited_once()

    async def test_main_closes_container_on_error(self) -> None:
        """main closes container even if publisher raises an error."""
        with (
            patch("src.workers.outbox_publisher.run_outbox_publish_worker.create_di_container") as mock_create,
            patch("src.workers.outbox_publisher.run_outbox_publish_worker.run_outbox_publish_worker") as mock_run,
        ):
            mock_container = AsyncMock()
            mock_create.return_value = mock_container
            mock_run.side_effect = RuntimeError("Publisher error")

            from src.workers.outbox_publisher.run_outbox_publish_worker import main

            with pytest.raises(RuntimeError, match="Publisher error"):
                await main()

        mock_container.close.assert_awaited_once()
