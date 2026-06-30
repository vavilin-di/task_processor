# Стратегия тестирования

## 1. Общая философия

Тесты являются неотъемлемой частью кодовой базы и гарантией того, что бизнес-логика работает корректно при любых изменениях.

**Цели тестирования:**
- Обеспечить регрессионную защиту при рефакторинге
- Документировать поведение системы через исполняемые спецификации
- Выявить ошибки на как можно более раннем этапе (shift-left)
- Поддерживать высокую скорость обратной связи (быстрые unit-тесты, выборочные integration-тесты)

---

## 2. Пирамида тестирования для данного проекта

- E2E: 1 сценарий (health-check, сквозной flow)
- Integration: ~20% тестов (репозитории + БД, роутеры + FastAPI TestClient, сервисы + БД)
- Unit: ~80% тестов (схемы, репозитории (mock), enums, утилиты, outbox worker, task processor worker, сервисы)

### 2.1. Unit-тесты (быстрые, без внешних зависимостей)

**Что тестируем:**
- [`src/enums.py`](src/enums.py) — корректность значений `StrEnum`
- [`src/schemas/`](src/schemas/) — Pydantic-валидация, сериализация/десериализация
- [`src/repositories/sqlalchemy_repository.py`](src/repositories/sqlalchemy_repository.py) — протокол/интерфейс (проверка контракта)
- [`src/repositories/tasks.py`](src/repositories/tasks.py) — логика `cancel_task`, `get_task_status` (с замокированным `SQLAlchemyRepository`)
- [`src/repositories/outbox_messages.py`](src/repositories/outbox_messages.py) — логика `add_error`, `mark_messages_as_published`, `get_not_published_outbox_messages` (с замокированным `SQLAlchemyRepository`)
- [`src/workers/utilities.py`](src/workers/utilities.py) — `use_broker` (контекстный менеджер)
- [`src/workers/outbox_publisher/outbox_publish_worker.py`](src/workers/outbox_publisher/outbox_publish_worker.py) — `process_batch` (с замокированными `session`, `broker`, `repo`)
- [`src/workers/task_processor/task_processor_worker.py`](src/workers/task_processor/task_processor_worker.py) — `_handle_task_message` (с замокированным контейнером и сервисом)
- [`src/services/tasks.py`](src/services/tasks.py) — `process_task`, `fail_task` (с замокированными репозиторием и сессией)
- [`src/settings/`](src/settings/) — корректность построения URL через model_validator

**Инструменты:** `pytest`, `pytest-asyncio`, `unittest.mock` / `pytest-mock`

### 2.2. Integration-тесты (с реальной БД)

**Что тестируем:**
- [`src/repositories/sqlalchemy_repository.py`](src/repositories/sqlalchemy_repository.py) — полный CRUD против реального PostgreSQL через testcontainers
- [`src/repositories/tasks.py`](src/repositories/tasks.py) — `cancel_task`, `get_task_status` с реальной БД
- [`src/repositories/outbox_messages.py`](src/repositories/outbox_messages.py) — `get_not_published_outbox_messages`, `mark_messages_as_published`, `add_error` с реальной БД
- [`src/routers/tasks.py`](src/routers/tasks.py) — HTTP-эндпоинты через `TestClient` FastAPI с реальной БД и замокированным брокером

**Инструменты:** `pytest`, `pytest-asyncio`, `httpx` (TestClient), `SQLAlchemy` + `asyncpg`, `testcontainers` (PostgreSQL)

### 2.3. E2E-тесты (smoke)

**Что тестируем:**
- Smoke-тест: запуск приложения, health-check (GET /tasks)

**Инструменты:** `httpx`, `testcontainers` (PostgreSQL)

---

## 3. Структура тестов

```
tests/
├── __init__.py
├── conftest.py                  # Общие фикстуры (engine, session, container, app)
├── unit/
│   ├── __init__.py
│   ├── test_enums.py
│   ├── test_schemas.py
│   ├── test_settings.py
│   ├── test_repositories/
│   │   ├── test_task_repository.py      # с mock
│   │   └── test_outbox_repository.py    # с mock
│   ├── test_mq/
│   │   ├── test_utilities.py
│   │   └── test_outbox_message_service.py
│   ├── test_services/
│   │   └── test_task_service.py         # process_task, fail_task (с mock)
│   └── test_workers/
│       └── test_task_processor_worker.py # _handle_task_message (с mock контейнера)
├── integration/
│   ├── __init__.py
│   ├── conftest.py              # Фикстуры для реальной БД (create_all / drop_all)
│   ├── test_sqlalchemy_repository.py
│   ├── test_task_repository.py
│   ├── test_outbox_repository.py
│   ├── test_task_service.py             # process_task, fail_task (с реальной БД)
│   └── test_routers/
│       ├── conftest.py          # TestClient + DI override
│       └── test_tasks_router.py
└── e2e/
    ├── __init__.py
    ├── conftest.py
    └── test_health_check.py
```

---

## 4. Инструменты и конфигурация

### 4.1. Зависимости (добавить в `pyproject.toml`)

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-mock>=3.14.0",
    "httpx>=0.27.0",
    "testcontainers>=4.0.0",   # PostgreSQL testcontainer для integration/e2e-тестов
]
```

### 4.2. Конфигурация pytest (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
filterwarnings = [
    "ignore::DeprecationWarning",
]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (require database)",
    "e2e: End-to-end tests (require full stack)",
]
```

### 4.3. Makefile-команды

```makefile
test:
	uv run pytest -v

test_unit:
	uv run pytest -v -m unit

test_integration:
	uv run pytest -v -m integration

test_cov:
	uv run pytest -v --cov=src --cov-report=term-missing --cov-report=html
```

---

## 5. Фикстуры (conftest.py)

Исходный код всех тестовых фикстур находится в следующих файлах:

- [`tests/conftest.py`](tests/conftest.py) — общие фикстуры для всех тестов:
  - `SharedPostgresContainer` — singleton-обёртка для PostgreSQL testcontainer (Docker)
  - `pg_engine` — PostgreSQL engine из общего testcontainer
  - `pg_session` — свежая транзакция на каждый тест с откатом
  - `container` — DI-контейнер без DatabaseProvider (для unit-тестов с моками)
  - `pytest_sessionfinish` — остановка Docker-контейнера после сессии

- [`tests/integration/conftest.py`](tests/integration/conftest.py) — фикстуры для integration-тестов:
  - `TestSessionProvider` — Dishka-провайдер, создающий сессию из общего engine
  - `TestBrokerProvider` — Dishka-провайдер с замокированным RabbitBroker
  - `session` — транзакция для прямого доступа к репозиторию
  - `di_container` — DI-контейнер с PostgreSQL и замокированным брокером
  - `app` — FastAPI приложение с тестовым DI
  - `client` — HTTP-клиент (TestClient) для тестирования эндпоинтов

- [`tests/e2e/conftest.py`](tests/e2e/conftest.py) — фикстуры для e2e-тестов:
  - `TestE2ESessionProvider`, `TestE2EBrokerProvider` — аналоги integration, но для e2e
  - `e2e_di_container`, `e2e_app`, `client` — для smoke health-check

---

## 6. Примеры тестов

### 6.1. Unit-тест: enums

```python
# tests/unit/test_enums.py
import pytest
from src.enums import TaskStatus, TaskPriority


class TestTaskStatus:
    def test_members_count(self):
        assert len(TaskStatus) == 6

    def test_values(self):
        assert TaskStatus.NEW == "Новая задача"
        assert TaskStatus.CANCELLED == "Отменена"

    def test_all_members_are_unique(self):
        values = [m.value for m in TaskStatus]
        assert len(values) == len(set(values))


class TestTaskPriority:
    def test_members_count(self):
        assert len(TaskPriority) == 3

    def test_order(self):
        assert list(TaskPriority) == [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH]
```

### 6.2. Unit-тест: схемы (Pydantic)

```python
# tests/unit/test_schemas.py
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.enums import TaskPriority, TaskStatus
from src.schemas.tasks import TaskCreate, Task, TaskFilter


class TestTaskCreate:
    def test_valid(self):
        data = {
            "name": "Test task",
            "description": "Description",
            "priority": TaskPriority.HIGH,
            "status": TaskStatus.NEW,
            "created_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "result": {"key": "value"},
            "errors": None,
            "is_active": True,
        }
        task = TaskCreate(**data)
        assert task.name == "Test task"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            TaskCreate()

    def test_from_attributes(self):
        """Проверяем, что модель можно создать из ORM-объекта (from_attributes=True)."""
        data = {
            "id": 1,
            "name": "Test",
            "description": "Desc",
            "priority": TaskPriority.MEDIUM,
            "status": TaskStatus.NEW,
            "created_at": datetime.now(timezone.utc),
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "result": {},
            "errors": [],
            "is_active": True,
        }
        task = Task.model_validate(data)
        assert task.id == 1


class TestTaskFilter:
    def test_all_none(self):
        filter_ = TaskFilter()
        assert filter_.model_dump(exclude_none=True) == {}

    def test_with_values(self):
        filter_ = TaskFilter(name="test", status=TaskStatus.NEW)
        dumped = filter_.model_dump(exclude_none=True)
        assert dumped == {"name": "test", "status": TaskStatus.NEW}
```

### 6.3. Unit-тест: TaskRepository (с mock)

```python
# tests/unit/test_repositories/test_task_repository.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.enums import TaskStatus
from src.repositories.tasks import TaskRepository


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def task_repo(mock_session):
    with patch("src.repositories.tasks.SQLAlchemyRepository.__init__", return_value=None):
        repo = TaskRepository.__new__(TaskRepository)
        repo._session = mock_session
        repo._model = MagicMock()
        return repo


class TestTaskRepository:
    async def test_cancel_task_calls_update_with_cancelled(self, task_repo, mock_session):
        task_repo.update = AsyncMock(return_value=MagicMock())
        result = await task_repo.cancel_task(record_id=1)
        task_repo.update.assert_awaited_once_with(record_id=1, status=TaskStatus.CANCELLED)
        assert result is not None

    async def test_cancel_task_returns_none_when_not_found(self, task_repo, mock_session):
        task_repo.update = AsyncMock(return_value=None)
        result = await task_repo.cancel_task(record_id=999)
        assert result is None

    async def test_get_task_status(self, task_repo, mock_session):
        task_repo.get_value = AsyncMock(return_value=TaskStatus.NEW)
        status = await task_repo.get_task_status(record_id=1)
        assert status == TaskStatus.NEW
        task_repo.get_value.assert_awaited_once_with(1, task_repo._model.status)
```

### 6.4. Unit-тест: OutboxMessageRepository (с mock)

```python
# tests/unit/test_repositories/test_outbox_repository.py
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from sqlalchemy import Select

from src.repositories.outbox_messages import OutboxMessageRepository, MAX_PUBLISH_ERRORS_COUNT


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def outbox_repo(mock_session):
    with patch("src.repositories.outbox_messages.SQLAlchemyRepository.__init__", return_value=None):
        repo = OutboxMessageRepository.__new__(OutboxMessageRepository)
        repo._session = mock_session
        repo._model = MagicMock()
        repo._model.id = PropertyMock()
        repo._model.routing_key = PropertyMock()
        repo._model.is_published = PropertyMock()
        repo._model.is_failed = PropertyMock()
        repo._model.created_at = PropertyMock()
        return repo


class TestOutboxMessageRepository:
    async def test_get_not_published_outbox_messages(self, outbox_repo, mock_session):
        mock_result = MagicMock()
        mock_result.t.all.return_value = [(1, "task.created"), (2, "task.updated")]
        mock_session.execute.return_value = mock_result

        result = await outbox_repo.get_not_published_outbox_messages(limit=10)
        assert result == [(1, "task.created"), (2, "task.updated")]
        mock_session.execute.assert_awaited_once()

    async def test_mark_messages_as_published(self, outbox_repo, mock_session):
        outbox_repo.update = AsyncMock()
        await outbox_repo.mark_messages_as_published(message_ids=[1])
        outbox_repo.update.assert_awaited_once()

    async def test_add_error_below_threshold(self, outbox_repo, mock_session):
        outbox_repo.get_value = AsyncMock(return_value=1)
        outbox_repo.update = AsyncMock()

        await outbox_repo.add_error(task_id=1, error="Some error")

        outbox_repo.update.assert_awaited_once()
        args, kwargs = outbox_repo.update.call_args
        assert kwargs["record_id"] == 1

    async def test_add_error_exceeds_threshold_marks_failed(self, outbox_repo, mock_session):
        outbox_repo.get_value = AsyncMock(return_value=MAX_PUBLISH_ERRORS_COUNT)
        outbox_repo.update = AsyncMock()

        await outbox_repo.add_error(task_id=1, error="Fatal error")

        # Должен быть вызван update с is_failed=True
        update_calls = outbox_repo.update.call_args_list
        last_call = update_calls[-1]
        assert "is_failed" in str(last_call.kwargs) or any(
            "is_failed" in str(k) for k in last_call.kwargs.values()
        )
```

### 6.5. Unit-тест: OutboxPublishWorker

```python
# tests/unit/test_mq/test_outbox_publish_worker.py
from unittest.mock import AsyncMock

import pytest

from src.workers.outbox_publisher.outbox_publish_worker import process_batch


class TestProcessBatch:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.begin = AsyncMock()
        session.begin.return_value = AsyncMock()
        session.begin.return_value = AsyncMock()
        return session

    @pytest.fixture
    def mock_broker(self):
        broker = AsyncMock()
        broker.publish = AsyncMock()
        return broker

    @pytest.fixture
    def mock_repo(self):
        repo = AsyncMock()
        repo.get_not_published_outbox_messages = AsyncMock()
        repo.mark_messages_as_published = AsyncMock()
        repo.add_error = AsyncMock()
        return repo

    async def test_publishes_all_messages(self, mock_session, mock_broker, mock_repo):
        mock_repo.get_not_published_outbox_messages.return_value = [(1, "task.created"), (2, "task.updated")]

        await process_batch(mock_session, mock_broker, mock_repo)

        assert mock_broker.publish.await_count == 2
        assert mock_repo.mark_messages_as_published.await_count == 2

    async def test_handles_publish_error(self, mock_session, mock_broker, mock_repo):
        mock_repo.get_not_published_outbox_messages.return_value = [(1, "task.created")]
        mock_broker.publish.side_effect = Exception("Connection lost")

        await process_batch(mock_session, mock_broker, mock_repo)

        mock_repo.add_error.assert_awaited_once_with(1, "Connection lost")
        mock_repo.mark_messages_as_published.assert_not_awaited()

    async def test_empty_batch(self, mock_session, mock_broker, mock_repo):
        mock_repo.get_not_published_outbox_messages.return_value = []

        await process_batch(mock_session, mock_broker, mock_repo)

        mock_broker.publish.assert_not_awaited()
        mock_repo.mark_messages_as_published.assert_not_awaited()
```

### 6.6. Integration-тест: SQLAlchemyRepository

```python
# tests/integration/test_sqlalchemy_repository.py
import pytest
from sqlalchemy import select

from src.database.models.tasks import Task
from src.enums import TaskPriority, TaskStatus
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository


@pytest.fixture
def repo(pg_session):
    return SQLAlchemyRepository(Task, pg_session)


class TestSQLAlchemyRepository:
    async def test_create_and_get(self, repo, pg_session):
        task = await repo.create(
            name="Test",
            description="Desc",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.NEW,
        )
        assert task.id is not None
        assert task.name == "Test"

        fetched = await repo.get(task.id)
        assert fetched is not None
        assert fetched.id == task.id

    async def test_get_returns_none_for_inactive(self, repo, pg_session):
        task = await repo.create(
            name="To delete",
            description="Desc",
            priority=TaskPriority.LOW,
            status=TaskStatus.NEW,
        )
        await repo.delete(task.id)

        fetched = await repo.get(task.id)
        assert fetched is None

    async def test_get_all_with_cursor_pagination(self, repo, pg_session):
        for i in range(5):
            await repo.create(
                name=f"Task {i}",
                description=f"Desc {i}",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.NEW,
            )

        items, cursor, has_next = await repo.get_all(cursor=None, limit=3)
        assert len(items) == 3
        assert has_next is True
        assert cursor is not None

    async def test_get_all_with_filters(self, repo, pg_session):
        await repo.create(
            name="High priority",
            description="Desc",
            priority=TaskPriority.HIGH,
            status=TaskStatus.NEW,
        )
        await repo.create(
            name="Low priority",
            description="Desc",
            priority=TaskPriority.LOW,
            status=TaskStatus.NEW,
        )

        items, _, _ = await repo.get_all(cursor=None, limit=10, filters={"priority": TaskPriority.HIGH})
        assert len(items) == 1
        assert items[0].name == "High priority"

    async def test_update(self, repo, pg_session):
        task = await repo.create(
            name="Original",
            description="Desc",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.NEW,
        )
        updated = await repo.update(task.id, name="Updated")
        assert updated is not None
        assert updated.name == "Updated"

    async def test_update_returns_none_for_missing(self, repo, pg_session):
        result = await repo.update(999, name="Nope")
        assert result is None

    async def test_delete_sets_inactive(self, repo, pg_session):
        task = await repo.create(
            name="To delete",
            description="Desc",
            priority=TaskPriority.LOW,
            status=TaskStatus.NEW,
        )
        await repo.delete(task.id)

        stmt = select(Task).where(Task.id == task.id)
        result = await pg_session.execute(stmt)
        deleted_task = result.scalar_one()
        assert deleted_task.is_active is False
```

### 6.7. Integration-тест: роутер задач

```python
# tests/integration/test_routers/test_tasks_router.py
import pytest
from httpx import AsyncClient
from starlette import status as status_codes


class TestTasksRouter:
    @pytest.mark.integration
    async def test_create_task(self, client: AsyncClient):
        payload = {
            "name": "Integration test task",
            "description": "Created via API",
            "priority": "Высокий",
            "status": "Новая задача",
        }
        response = await client.post("/tasks", json=payload)
        assert response.status_code == status_codes.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Integration test task"
        assert data["id"] is not None

    @pytest.mark.integration
    async def test_get_task_not_found(self, client: AsyncClient):
        response = await client.get("/tasks/9999")
        assert response.status_code == status_codes.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Задача не найдена"

    @pytest.mark.integration
    async def test_get_tasks_pagination(self, client: AsyncClient):
        response = await client.get("/tasks", params={"limit": 5})
        assert response.status_code == status_codes.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "next_cursor" in data
        assert "has_next" in data

    @pytest.mark.integration
    async def test_cancel_task(self, client: AsyncClient):
        # Сначала создаём задачу
        create_resp = await client.post("/tasks", json={
            "name": "To cancel",
            "description": "Will be cancelled",
            "priority": "Средний",
            "status": "Новая задача",
        })
        task_id = create_resp.json()["id"]

        # Отменяем
        cancel_response = await client.delete(f"/tasks/{task_id}")
        assert cancel_response.status_code == status_codes.HTTP_200_OK
        assert cancel_response.json()["status"] == "Отменена"

    @pytest.mark.integration
    async def test_get_task_status(self, client: AsyncClient):
        create_resp = await client.post("/tasks", json={
            "name": "Status check",
            "description": "Check status endpoint",
            "priority": "Низкий",
            "status": "Новая задача",
        })
        task_id = create_resp.json()["id"]

        status_response = await client.get(f"/tasks/{task_id}/status")
        assert status_response.status_code == status_codes.HTTP_200_OK
        assert status_response.json() == "Новая задача"
```

---

## 7. Запуск тестов

### 7.1. Быстрый запуск (unit-тесты)

```bash
make test_quick
# или
uv run pytest -v -m "not integration and not e2e"
```

### 7.2. Все тесты

```bash
make test
# или
uv run pytest -v
```

### 7.3. С покрытием

```bash
make test_cov
# или
uv run pytest -v --cov=src --cov-report=term-missing --cov-report=html
```

### 7.4. Только integration-тесты (требуют БД)

```bash
make test_integration
# или
uv run pytest -v -m integration
```

---

## 8. Best Practices

### 8.1. Arrange-Act-Assert (AAA)

Каждый тест должен быть разделён на три логические части:

```python
# Arrange
repo = SQLAlchemyRepository(Task, session)
task_data = {"name": "Test", "description": "Desc", ...}

# Act
task = await repo.create(**task_data)

# Assert
assert task.id is not None
assert task.name == "Test"
```

### 8.2. Один тест — одна проверка

Каждый тест проверяет ровно одно поведение. Если нужно проверить несколько аспектов — пишите несколько тестов.

### 8.3. Изолированность тестов

- Unit-тесты не должны иметь внешних зависимостей (БД, сеть, файловая система)
- Integration-тесты должны работать с изолированной БД (PostgreSQL через testcontainers)
- Каждый тест начинается с чистого состояния (фикстуры с откатом транзакции)

### 8.4. Наименование тестов

Шаблон: `test_{method_name}__{scenario}__{expected_result}`

```python
async def test_create__valid_data__returns_task_with_id():
async def test_get__missing_id__returns_none():
async def test_cancel_task__existing_task__sets_status_cancelled():
```

### 8.5. Фикстуры

- Фикстуры должны быть минимальными и переиспользуемыми
- `scope="session"` для тяжёлых объектов (engine), `scope="function"` для изменяемого состояния (session)
- Избегать фикстур, которые не используются во всех тестах модуля

### 8.6. Моки

- Мокать только внешние границы (БД, брокер, HTTP-клиенты)
- Не мокать то, чем вы владеете (собственные схемы, утилиты, enums)
- Использовать `AsyncMock` для асинхронных вызовов
- Проверять, что мок был вызван с ожидаемыми аргументами (`assert_called_once_with`)

---

## 9. CI/CD интеграция

### 9.1. GitHub Actions (реальный pipeline)

Тесты запускаются через [`testing.yml`](.github/workflows/testing.yml), который вызывается из [`ci.yml`](.github/workflows/ci.yml).

**Jobs:**
1. **unit-tests** — быстрые тесты без внешних зависимостей, с coverage
2. **integration-tests** — с PostgreSQL service container (postgres:14.5), с coverage
3. **e2e-tests** — smoke health-check, с PostgreSQL service container

```yaml
# .github/workflows/testing.yml
name: testing

on:
  workflow_call:

env:
  POSTGRES_HOST: localhost
  POSTGRES_PORT: 5432
  POSTGRES_DATABASE: test_db
  POSTGRES_USER: test_user
  POSTGRES_PASSWORD: test_pass

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Run unit tests with coverage
        run: uv run pytest -v -m unit --cov=src --cov-report=xml:coverage-unit.xml
      - name: Upload unit coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-unit
          path: coverage-unit.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:14.5
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Run integration tests with coverage
        run: uv run pytest -v -m integration --cov=src --cov-report=xml:coverage-integration.xml --cov-append
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DATABASE }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
      - name: Upload integration coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-integration
          path: coverage-integration.xml

  e2e-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: postgres:14.5
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Run e2e tests
        run: uv run pytest -v -m e2e
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DATABASE }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
```

---

## 8. Мокирование Dishka-контейнера в unit-тестах

При тестировании воркеров, которые используют `async with container() as request_container`, необходимо правильно настроить мок контейнера.

### Проблема

`container` — это `MagicMock`. Вызов `container()` возвращает `container.return_value`. `async with` на возвращённом объекте вызывает `__aenter__`.

### Решение

```python
@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    request_container = MagicMock()
    # container() возвращает request_container
    container.return_value = request_container
    # async with на request_container вызывает его __aenter__
    request_container.__aenter__ = AsyncMock(return_value=request_container)
    request_container.__aexit__ = AsyncMock()
    return container
```

В тесте настройка `request_container.get`:

```python
async def _setup_get(self, mock_container: MagicMock, mock_task_service: MockTaskService) -> None:
    request_container = mock_container.return_value

    async def get_side_effect(*args: object, **kwargs: object) -> MockTaskService:
        return mock_task_service

    request_container.get = get_side_effect
```

Ключевые моменты:
1. `container.return_value = request_container` — чтобы `container()` возвращал `request_container`
2. `request_container.__aenter__` — `AsyncMock`, возвращающий `request_container`
3. `request_container.get` — **async-функция** (не `AsyncMock`), возвращающая замокированный сервис
4. Сам сервис — простой класс с `AsyncMock`-методами (не `MagicMock`), чтобы избежать перехвата атрибутов

---

## 9. Timezone-совместимость с PostgreSQL

При работе с `DateTime()` колонками в PostgreSQL (без `timezone=True`) необходимо передавать offset-naive datetime.

### Проблема

```python
from datetime import UTC, datetime

# datetime.now(UTC) возвращает offset-aware datetime
# PostgreSQL колонка DateTime() (без timezone) ожидает offset-naive
started_at=datetime.now(UTC)  # TypeError: can't subtract offset-naive and offset-aware datetimes
```

### Решение

```python
from datetime import UTC, datetime

# .replace(tzinfo=None) делает datetime offset-naive
started_at=datetime.now(UTC).replace(tzinfo=None)
```

### Когда это важно

- Интеграционные тесты с реальной PostgreSQL через testcontainers
- Любые запросы на запись/обновление `DateTime()` полей без timezone
- Unit-тесты эту проблему не ловят, т.к. используют моки

---

## 10. Нагрузочное тестирование (Load Testing)

### 10.1. Инструмент: Locust

Для нагрузочного тестирования используется [Locust](https://locust.io/) — Python-фреймворк для симуляции пользовательской нагрузки.

**Файл сценариев:** [`tests/load/locustfile.py`](tests/load/locustfile.py)

### 10.2. Сценарии нагрузки

В файле реализовано три класса пользователей:

| Класс                | Описание                                                | Вес задач                                                         |
| -------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| `TaskApiUser`        | Смешанная нагрузка: создание, чтение, отмена задач      | POST (5), GET list (3), GET by id (2), GET status (1), DELETE (1) |
| `TaskCreateOnlyUser` | Только создание задач — максимальная нагрузка на запись | POST (1)                                                          |
| `TaskReadOnlyUser`   | Только чтение — нагрузка на GET-эндпоинты               | GET list (4), GET by id (2), GET status (1)                       |

### 10.3. Запуск

```bash
make load_test_web
```

Веб-интерфейс будет доступен по адресу: http://localhost:8089

### 10.4. Метрики и целевые показатели (SLO)

| Метрика                       | Цель     | Критично |
| ----------------------------- | -------- | -------- |
| `p95 latency POST /tasks`     | < 500ms  | Да       |
| `p99 latency POST /tasks`     | < 1s     | Да       |
| Error rate                    | < 1%     | Да       |
| Throughput создания задач     | > 50 rps | Да       |
| `p95 latency GET /tasks`      | < 300ms  | Да       |
| `p95 latency GET /tasks/{id}` | < 200ms  | Нет      |
