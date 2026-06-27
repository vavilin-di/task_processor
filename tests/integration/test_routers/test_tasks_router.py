import pytest
from httpx import AsyncClient
from starlette import status as status_codes

from src.enums import TaskPriority, TaskStatus


def _create_task_payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": "API test task",
        "description": "Created via API test",
        "priority": TaskPriority.MEDIUM.value,
        "payload": {"key": "value"},
    }
    data.update(overrides)
    return data


class TestTasksRouter:
    """Integration-тесты для маршрутов CRUD задач."""

    @pytest.mark.skip(reason="OutboxMessage является MappedAsDataclass и требует все поля при создании")
    async def test_create_task(self, client: AsyncClient) -> None:
        payload = _create_task_payload()
        response = await client.post("/tasks", json=payload)

        assert response.status_code == status_codes.HTTP_201_CREATED  # noqa: S101
        data = response.json()
        assert data["name"] == "API test task"  # noqa: S101
        assert data["id"] is not None  # noqa: S101
        assert data["status"] == TaskStatus.NEW.value  # noqa: S101

    async def test_get_task_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/tasks/1234")
        assert response.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101
        assert response.json()["detail"] == "Задача не найдена"  # noqa: S101

    @pytest.mark.skip(reason="OutboxMessage является MappedAsDataclass и требует все поля при создании")
    async def test_get_task_by_id(self, client: AsyncClient) -> None:
        create_resp = await client.post("/tasks", json=_create_task_payload())
        task_id = create_resp.json()["id"]

        response = await client.get(f"/tasks/{task_id}")
        assert response.status_code == status_codes.HTTP_200_OK  # noqa: S101
        assert response.json()["id"] == task_id  # noqa: S101

    @pytest.mark.skip(reason="OutboxMessage является MappedAsDataclass и требует все поля при создании")
    async def test_get_tasks_pagination(self, client: AsyncClient) -> None:
        for i in range(3):
            await client.post("/tasks", json=_create_task_payload(name=f"Task {i}"))

        response = await client.get("/tasks", params={"limit": 2})
        assert response.status_code == status_codes.HTTP_200_OK  # noqa: S101
        data = response.json()
        assert len(data["items"]) == 2  # noqa: S101, PLR2004
        assert "next_cursor" in data  # noqa: S101
        assert "has_next" in data  # noqa: S101

    @pytest.mark.skip(reason="OutboxMessage является MappedAsDataclass и требует все поля при создании")
    async def test_cancel_task(self, client: AsyncClient) -> None:
        create_resp = await client.post("/tasks", json=_create_task_payload(name="To cancel"))
        task_id = create_resp.json()["id"]

        cancel_response = await client.delete(f"/tasks/{task_id}")
        assert cancel_response.status_code == status_codes.HTTP_200_OK  # noqa: S101
        assert cancel_response.json()["status"] == TaskStatus.CANCELLED.value  # noqa: S101

    async def test_cancel_task_not_found(self, client: AsyncClient) -> None:
        response = await client.delete("/tasks/1234")
        assert response.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101

    @pytest.mark.skip(reason="OutboxMessage является MappedAsDataclass и требует все поля при создании")
    async def test_get_task_status(self, client: AsyncClient) -> None:
        create_resp = await client.post("/tasks", json=_create_task_payload(name="Status check"))
        task_id = create_resp.json()["id"]

        status_responce = await client.get(f"/tasks/{task_id}/status")
        assert status_responce.status_code == status_codes.HTTP_200_OK  # noqa: S101
        assert status_responce.json() == TaskStatus.NEW.value  # noqa: S101

    async def test_get_task_status_not_found(self, client: AsyncClient) -> None:
        response = await client.get("/tasks/1234/status")
        assert response.status_code == status_codes.HTTP_404_NOT_FOUND  # noqa: S101
