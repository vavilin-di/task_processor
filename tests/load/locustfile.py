"""Locust-файл для нагрузочного тестирования HTTP API task_processor.

Запуск:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

С веб-интерфейсом:
    locust -f tests/load/locustfile.py --host=http://localhost:8000 --web-host=0.0.0.0 --web-port=8089

Без веб-интерфейса (headless):
    locust -f tests/load/locustfile.py --host=http://localhost:8000 \
        --headless --users=50 --spawn-rate=5 --run-time=5m \
        --csv=tests/load/reports/report
"""

from __future__ import annotations

import random
from http import HTTPStatus
from typing import Any

from locust import HttpUser, between, task

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

TASK_TITLES = [
    "Настроить CI/CD pipeline",
    "Обновить зависимости проекта",
    "Рефакторинг модуля аутентификации",
    "Добавить интеграционные тесты",
    "Оптимизировать SQL-запросы",
    "Написать документацию API",
    "Исправить баг с пагинацией",
    "Добавить мониторинг через Prometheus",
    "Обновить Dockerfile",
    "Провести code review",
]

TASK_PRIORITIES = ["Низкий", "Средний", "Высокий"]

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _random_task_payload() -> dict[str, Any]:
    """Генерирует случайный payload для создания задачи."""
    return {
        "name": f"{random.choice(TASK_TITLES)} #{random.randint(1, 100_000)}",  # noqa: S311
        "description": "Нагрузочное тестирование",
        "priority": random.choice(TASK_PRIORITIES),  # noqa: S311
        "payload": {"source": "load_test", "iteration": random.randint(1, 1_000_000)},  # noqa: S311
    }


# ---------------------------------------------------------------------------
# Пользовательские сценарии
# ---------------------------------------------------------------------------


class TaskApiUser(HttpUser):
    """Сценарий: смешанная нагрузка на все эндпоинты задач."""

    wait_time = between(0.5, 3.0)

    def on_start(self) -> None:
        """При старте сессии — создаём несколько задач, чтобы было что запрашивать."""
        self._created_ids: list[int] = []
        for _ in range(5):
            with self.client.post(
                f"{API_PREFIX}/tasks",
                json=_random_task_payload(),
                catch_response=True,
                name="[Setup] POST /tasks",
            ) as resp:
                if resp.status_code == HTTPStatus.CREATED:
                    resp_json = resp.json()
                    data: dict[str, Any] = {} if not isinstance(resp_json, dict) else resp_json
                    task_id = data.get("id")
                    if task_id is not None:
                        self._created_ids.append(task_id)

    @task(5)
    def create_task(self) -> None:
        """POST /api/v1/tasks — создание новой задачи."""
        with self.client.post(
            f"{API_PREFIX}/tasks",
            json=_random_task_payload(),
            catch_response=True,
            name="POST /tasks",
        ) as resp:
            if resp.status_code == HTTPStatus.CREATED:
                resp_json = resp.json()
                data: dict[str, Any] = {} if not isinstance(resp_json, dict) else resp_json
                task_id = data.get("id")
                if task_id is not None:
                    self._created_ids.append(task_id)
                resp.success()
            elif resp.status_code == HTTPStatus.CONFLICT:
                resp.success()  # конфликт — допустимо при конкурентном доступе
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(3)
    def get_tasks_list(self) -> None:
        """GET /api/v1/tasks — получение списка задач."""
        params: dict[str, str | int] = {"limit": random.choice([10, 20, 50])}  # noqa: S311
        if random.random() < 0.3:  # noqa: PLR2004, S311
            params["status"] = random.choice(["Новая задача", "В работе", "Завершена"])  # noqa: S311

        with self.client.get(
            f"{API_PREFIX}/tasks",
            params=params,
            catch_response=True,
            name="GET /tasks",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def get_task_by_id(self) -> None:
        """GET /api/v1/tasks/{id} — получение задачи по ID."""
        if not self._created_ids:
            return

        task_id = random.choice(self._created_ids)  # noqa: S311
        with self.client.get(
            f"{API_PREFIX}/tasks/{task_id}",
            catch_response=True,
            name="GET /tasks/{id}",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            elif resp.status_code == HTTPStatus.NOT_FOUND:
                # задача могла быть удалена — убираем из списка
                self._created_ids.remove(task_id)
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def get_task_status(self) -> None:
        """GET /api/v1/tasks/{id}/status — получение статуса задачи."""
        if not self._created_ids:
            return

        task_id = random.choice(self._created_ids)  # noqa: S311
        with self.client.get(
            f"{API_PREFIX}/tasks/{task_id}/status",
            catch_response=True,
            name="GET /tasks/{id}/status",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            elif resp.status_code == HTTPStatus.NOT_FOUND:
                self._created_ids.remove(task_id)
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def cancel_task(self) -> None:
        """DELETE /api/v1/tasks/{id} — отмена задачи."""
        if not self._created_ids:
            return

        task_id = random.choice(self._created_ids)  # noqa: S311
        with self.client.delete(
            f"{API_PREFIX}/tasks/{task_id}",
            catch_response=True,
            name="DELETE /tasks/{id}",
        ) as resp:
            if resp.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND):
                self._created_ids.remove(task_id)
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class TaskCreateOnlyUser(HttpUser):
    """Сценарий: только создание задач — максимальная нагрузка на запись."""

    wait_time = between(0.1, 0.5)

    @task
    def create_task(self) -> None:
        """Максимальный поток создания задач."""
        with self.client.post(
            f"{API_PREFIX}/tasks",
            json=_random_task_payload(),
            catch_response=True,
            name="POST /tasks (write-only)",
        ) as resp:
            if resp.status_code in (HTTPStatus.CREATED, HTTPStatus.CONFLICT):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


class TaskReadOnlyUser(HttpUser):
    """Сценарий: только чтение — нагрузка на GET-эндпоинты."""

    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        """Создаём одну задачу для тестов чтения."""
        with self.client.post(
            f"{API_PREFIX}/tasks",
            json=_random_task_payload(),
            catch_response=True,
            name="[Setup] POST /tasks",
        ) as resp:
            if resp.status_code == HTTPStatus.CREATED:
                resp_json = resp.json()
                data: dict[str, Any] = {} if not isinstance(resp_json, dict) else resp_json
                self._target_id = data.get("id")
            else:
                self._target_id = None

    @task(4)
    def get_tasks_list(self) -> None:
        """GET /api/v1/tasks."""
        with self.client.get(
            f"{API_PREFIX}/tasks",
            params={"limit": 20},
            catch_response=True,
            name="GET /tasks (read-only)",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def get_task_by_id(self) -> None:
        """GET /api/v1/tasks/{id}."""
        if self._target_id is None:
            return
        with self.client.get(
            f"{API_PREFIX}/tasks/{self._target_id}",
            catch_response=True,
            name="GET /tasks/{id} (read-only)",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def get_task_status(self) -> None:
        """GET /api/v1/tasks/{id}/status."""
        if self._target_id is None:
            return
        with self.client.get(
            f"{API_PREFIX}/tasks/{self._target_id}/status",
            catch_response=True,
            name="GET /tasks/{id}/status (read-only)",
        ) as resp:
            if resp.status_code == HTTPStatus.OK:
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")
