import pytest
from httpx import AsyncClient


@pytest.mark.e2e
class TestHealthCheck:
    """E2E smoke-тест: проверка запуска приложения."""

    async def test_health_check(self, client: AsyncClient) -> None:
        """Проверка, что приложение отвечает на HTTP-запрос."""
        response = await client.get("/tasks")
        assert response.status_code == 200  # noqa: S101
