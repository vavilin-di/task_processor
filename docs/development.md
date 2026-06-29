# Инструкция для разработчика

## 1. Начало работы

### Требования

- Python 3.12
- PostgreSQL 14+
- RabbitMQ 3.11+
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов

### Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/vavilin-di/task_processor.git # (либо необходимая ветка)
cd task_processor

# 2. Создать файл .env из шаблона
cp .env.example .env
# или вручную создать .env (см. раздел «Переменные окружения»)

# 3. Установить зависимости и применить миграции
make install

# 4. Запустить dev-сервер
make dev
```

После выполнения этих шагов сервер будет доступен по адресу: `http://127.0.0.1:8080`.

Документация API (Swagger): `http://127.0.0.1:8080/docs`.

---

## 2. Переменные окружения

Файл `.env` должен находиться в корне проекта (`src/settings/common.py` ищет `.env` относительно `BASE_DIR`).

| Переменная                | Тип                                    | Значение по умолчанию                    | Описание                                                                             |
| ------------------------- | -------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| **PostgreSQL**            |                                        |                                          |                                                                                      |
| `POSTGRES_HOST`           | `str`                                  | —                                        | Хост PostgreSQL                                                                      |
| `POSTGRES_PORT`           | `int`                                  | —                                        | Порт PostgreSQL                                                                      |
| `POSTGRES_USER`           | `str`                                  | —                                        | Пользователь PostgreSQL                                                              |
| `POSTGRES_PASSWORD`       | `str`                                  | —                                        | Пароль PostgreSQL                                                                    |
| `POSTGRES_DATABASE`       | `str`                                  | —                                        | Имя базы данных                                                                      |
| `POSTGRES_POOL_SIZE`      | `int`                                  | —                                        | Размер пула соединений                                                               |
| `POSTGRES_MAX_OVERFLOW`   | `int`                                  | —                                        | Максимальное количество соединений сверх пула                                        |
| `POSTGRES_POOL_TIMEOUT`   | `int`                                  | —                                        | Таймаут ожидания соединения из пула (сек)                                            |
| `POSTGRES_POOL_RECYCLE`   | `int`                                  | —                                        | Время переиспользования соединения (сек)                                             |
| **RabbitMQ**              |                                        |                                          |                                                                                      |
| `RABBITMQ_HOST`           | `str`                                  | —                                        | Хост RabbitMQ                                                                        |
| `RABBITMQ_PORT`           | `int`                                  | —                                        | Порт RabbitMQ                                                                        |
| `RABBITMQ_USER`           | `str`                                  | —                                        | Пользователь RabbitMQ                                                                |
| `RABBITMQ_PASSWORD`       | `str`                                  | —                                        | Пароль RabbitMQ                                                                      |
| `RABBITMQ_VIRTUAL_HOST`   | `str`                                  | —                                        | Virtual host RabbitMQ                                                                |
| `RABBITMQ_PREFETCH_COUNT` | `int`                                  | —                                        | Количество сообщений, выдаваемых потребителю за раз                                  |
| `RABBITMQ_HEARTBEAT`      | `int`                                  | —                                        | Интервал heartbeat (сек)                                                             |
| **Приложение**            |                                        |                                          |                                                                                      |
| `APP_TITLE`               | `str`                                  | `Асинхронный сервис управления задачами` | Название приложения                                                                  |
| `APP_VERSION`             | `str`                                  | `0.1.0`                                  | Версия приложения                                                                    |
| `APP_ENV`                 | `Literal["development", "production"]` | `development`                            | Окружение                                                                            |
| `DEBUG`                   | `bool`                                 | `False`                                  | Режим отладки (автоматически устанавливается в `True` при `APP_ENV != "production"`) |
| `LOG_LEVEL`               | `str`                                  | `INFO`                                   | Уровень логирования                                                                  |
| `API_PREFIX`              | `str`                                  | `/api`                                   | Префикс пути API                                                                     |
| `API_VERSION_PREFIX`      | `str`                                  | `/v1`                                    | Префикс версии API                                                                   |
| `ALLOWED_HOSTS`           | `list[str]`                            | `["localhost", "127.0.0.1"]`             | Список разрешённых хостов                                                            |
| `CORS_ORIGINS`            | `list[AnyHttpUrl]`                     | `[]`                                     | Разрешённые CORS-источники                                                           |

---

## 3. Makefile команды

| Команда                            | Описание                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------------------------------- |
| `make install`                     | Установка зависимостей (`uv sync`) + применение миграций (`alembic upgrade head`)             |
| `make migrate`                     | Применить миграции до последней версии                                                        |
| `make lint`                        | Запуск всех линтеров и форматтеров: `black --check`, `ruff check`, `mypy`                     |
| `make check_models`                | Проверить соответствие моделей SQLAlchemy и миграций (`alembic check`)                        |
| `make dev`                         | Запуск dev-сервера: `uvicorn src:app --host 127.0.0.1 --port 8080 --reload`                   |
| `make start_outbox_publish_worker` | Запуск воркера публикации outbox-сообщений                                                    |
| `make start_dlq_consumer_worker`   | Запуск воркера обработки DLQ (Dead Letter Queue)                                              |
| `make start_main_app`              | Production-запуск: `uvicorn src:app --host $(HOST) --port $(PORT) --workers $(WORKERS_COUNT)` |
| `make test`                        | Запуск всех тестов                                                                            |
| `make test_unit`                   | Запуск unit-тестов (маркер `-m unit`)                                                         |
| `make test_integration`            | Запуск integration-тестов (маркер `-m integration`)                                           |
| `make test_cov`                    | Запуск тестов с отчётом о покрытии (`term-missing` + `html`)                                  |

Переменные, используемые в Makefile:

| Переменная      | Значение по умолчанию |
| --------------- | --------------------- |
| `HOST`          | `127.0.0.1`           |
| `PORT`          | `8080`                |
| `WORKERS_COUNT` | `1`                   |

Пример переопределения:

```bash
make dev HOST=0.0.0.0 PORT=8000
make start_main_app WORKERS_COUNT=4
```

---

## 4. Структура проекта

```
task_processor/
├── src/
│   ├── __init__.py
│   ├── app.py                          # FastAPI приложение, обработчики ошибок
│   ├── di.py                           # DI-контейнер Dishka
│   ├── enums.py                        # TaskStatus, TaskPriority (StrEnum)
│   ├── database/
│   │   ├── models/                     # SQLAlchemy модели
│   │   │   ├── base.py                 #   Базовый класс модели
│   │   │   ├── tasks.py                #   Модель Task
│   │   │   ├── outbox_messages.py      #   Модель OutboxMessage
│   │   │   └── dlq_messages.py         #   Модель DLQMessage
│   │   └── migrations/                 # Alembic миграции
│   │       ├── env.py                  #   Конфигурация окружения Alembic
│   │       ├── script.py.mako          #   Шаблон для создания миграций
│   │       └── versions/               #   Файлы миграций
│   ├── repositories/                   # Слой доступа к данным (Repository pattern)
│   │   ├── sqlalchemy_repository.py    #   Базовый SQLAlchemy репозиторий
│   │   ├── soft_delete_sqlalchemy_repository.py  # Репозиторий с soft-delete
│   │   ├── tasks.py                    #   Репозиторий задач
│   │   ├── outbox_messages.py          #   Репозиторий outbox-сообщений
│   │   └── dlq_messages.py             #   Репозиторий DLQ-сообщений
│   ├── routers/                        # FastAPI эндпоинты
│   │   ├── __init__.py                 #   Подключение роутеров
│   │   └── tasks.py                    #   Роутер задач
│   ├── schemas/                        # Pydantic схемы
│   │   ├── common.py                   #   Общие схемы (пагинация и др.)
│   │   ├── tasks.py                    #   Схемы задач
│   │   ├── outbox_messages.py          #   Схемы outbox-сообщений
│   │   └── dlq_messages.py             #   Схемы DLQ-сообщений
│   ├── services/                       # Бизнес-логика
│   │   ├── tasks.py                    #   Сервис задач
│   │   └── outbox_messages.py          #   Сервис outbox-сообщений
│   ├── settings/                       # Конфигурация приложения
│   │   ├── __init__.py                 #   Экспорт настроек
│   │   ├── common.py                   #   Общие константы (BASE_DIR, ENV_FILE_PATH)
│   │   ├── postgres.py                 #   PostgresSettings
│   │   ├── rabbit_mq.py                #   RabbitMQSettings
│   │   └── settings.py                 #   Settings (общая конфигурация)
│   ├── messaging/                      # Конфигурация RabbitMQ
│   │   └── queues.py                   #   Очереди, exchange, routing keys
│   └── workers/                        # Фоновые воркеры
│       ├── utilities.py                #   Общие утилиты для воркеров
│       ├── outbox_publisher/           #   Публикация outbox-сообщений
│       │   ├── outbox_publish_worker.py    #   Логика воркера
│       │   └── run_outbox_publish_worker.py # Точка входа
│       └── dlq_consumer/               #   Обработка DLQ
│           ├── dlq_consumer_worker.py      #   Логика воркера
│           └── run_dlq_consumer_worker.py  # Точка входа
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Общие фикстуры pytest
│   ├── unit/                           # Unit-тесты (mock, без внешних зависимостей)
│   │   ├── test_enums.py
│   │   ├── test_schemas.py
│   │   ├── test_settings.py
│   │   ├── test_mq/
│   │   │   ├── test_outbox_message_service.py
│   │   │   └── test_utilities.py
│   │   └── test_repositories/
│   │       ├── test_outbox_repository.py
│   │       └── test_task_repository.py
│   ├── integration/                    # Integration-тесты (реальная БД)
│   │   ├── __init__.py
│   │   ├── conftest.py                 #   Фикстуры для интеграционных тестов
│   │   ├── test_outbox_repository.py
│   │   ├── test_sqlalchemy_repository.py
│   │   ├── test_task_repository.py
│   │   └── test_routers/
│   │       ├── conftest.py
│   │       └── test_tasks_router.py
│   └── e2e/                            # E2E-тесты (полный стек)
│       ├── __init__.py
│       ├── conftest.py
│       └── test_health_check.py
├── infrastructure/
│   ├── .dockerignore
│   ├── Dockerfile                      # Multi-stage сборка
│   └── docker-compose.yml              # Docker Compose (postgres, rabbitmq, app, workers)
├── docs/
│   ├── administration.md               # Инструкция администратора
│   ├── api.md                          # API документация
│   ├── architecture.md                 # Архитектурная документация
│   ├── deployment.md                   # Инструкция по развёртыванию
│   ├── development.md                  # Данный файл
│   ├── outbox_pattern.md               # Transactional Outbox Pattern
│   └── testing.md                      # Стратегия тестирования
├── .github/workflows/                  # GitHub Actions
│   ├── ci.yml                          #   Основной CI-пайплайн
│   ├── code-quality-check.yml          #   Проверка качества кода
│   ├── testing.yml                     #   Тестирование
│   └── sonarcloud.yml                  #   Анализ SonarCloud
├── .env.example
├── alembic.ini                         # Конфигурация Alembic
├── Makefile                            # Makefile с командами
├── pyproject.toml                      # Зависимости и настройки инструментов
├── sonar-project.properties            # Конфигурация SonarCloud
└── uv.lock                             # Lock-файл зависимостей
```

---

## 5. Работа с миграциями

Управление миграциями осуществляется через Alembic.

```bash
# Применить все миграции до последней версии
make migrate

# Проверить соответствие моделей и миграций
make check_models

# Создать новую миграцию (автогенерация)
uv run alembic revision --autogenerate -m "описание изменений"

# Применить миграции до последней версии
uv run alembic upgrade head

# Откатить последнюю миграцию
uv run alembic downgrade -1

# Откатиться до конкретной ревизии
uv run alembic downgrade <revision_id>
```

**Важно:** После изменения SQLAlchemy-моделей всегда запускайте `make check_models`, чтобы убедиться, что миграции синхронизированы с моделями.

---

## 6. Линтеры и форматтеры

В проекте настроены три инструмента для контроля качества кода:

### Black

Форматтер кода с длиной строки **120 символов**.

```bash
# Проверить форматирование
uv run black --check --diff .

# Отформатировать код
uv run black .
```

### Ruff

Линтер с широким набором правил:

| Категория    | Правила               | Описание                           |
| ------------ | --------------------- | ---------------------------------- |
| `PLR`, `PLW` | pylint                | Рефакторинг и предупреждения       |
| `UP`         | pyupgrade             | Совместимость с современным Python |
| `E`, `W`     | pycodestyle           | Ошибки и предупреждения стиля      |
| `F`          | pyflakes              | Ошибки логики                      |
| `I`          | isort                 | Сортировка импортов                |
| `B`          | flake8-bugbear        | Поиск багов                        |
| `S`          | flake8-bandit         | Безопасность                       |
| `C`          | flake8-comprehensions | Улучшение comprehensions           |
| `T20`        | flake8-print          | Запрет `print()`                   |
| `SIM`        | flake8-simplify       | Упрощение кода                     |
| `RET`        | flake8-return         | Правила return                     |
| `TCH`        | flake8-type-checking  | Type-checking импорты              |
| `PERF`       | Perflint              | Производительность                 |
| `PTH`        | flake8-use-pathlib    | Использование pathlib              |
| `DTZ`        | flake8-datetimez      | Работа с часовыми поясами          |
| `EM`         | flake8-errmsg         | Сообщения об ошибках               |
| `RUF`        | Ruff-specific         | Специфичные правила Ruff           |

```bash
uv run ruff check .
uv run ruff check --fix .   # автоисправление
```

### Mypy

Статическая типизация с плагином Pydantic.

```bash
uv run mypy .
```

### Запуск всех проверок

```bash
make lint
```

---

## 7. Тестирование

### Команды

| Команда                 | Описание                                             |
| ----------------------- | ---------------------------------------------------- |
| `make test`             | Запуск всех тестов                                   |
| `make test_unit`        | Unit-тесты (`-m unit`)                               |
| `make test_integration` | Integration-тесты (`-m integration`)                 |
| `make test_cov`         | Тесты с отчётом о покрытии (`term-missing` + `html`) |

### Маркеры pytest

| Маркер        | Описание                                              |
| ------------- | ----------------------------------------------------- |
| `unit`        | Unit-тесты — быстрые, без внешних зависимостей (mock) |
| `integration` | Integration-тесты — требуют реальной PostgreSQL       |
| `e2e`         | E2E-тесты — требуют полного стека (БД + RabbitMQ)     |

### Конфигурация pytest ([`pyproject.toml`](pyproject.toml))

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (require database)",
    "e2e: End-to-end tests (require full stack)",
]
```

### Уровни тестирования

Подробное описание стратегии тестирования — в [`docs/testing.md`](docs/testing.md).

- **Unit-тесты** — тестирование изолированных компонентов с моками внешних зависимостей. Покрывают: схемы, enum'ы, настройки, сервисы, репозитории.
- **Integration-тесты** — тестирование с реальной PostgreSQL. Покрывают: SQLAlchemy-репозитории, роутеры FastAPI (через TestClient), outbox-репозиторий.
- **E2E-тесты** — тестирование полного цикла с реальными БД и RabbitMQ.

---

## 8. Локальный запуск воркеров

### Outbox Publisher Worker

```bash
make start_outbox_publish_worker
```

**Назначение:** Фоновый воркер, который периодически выбирает из таблицы `outbox_messages` неотправленные сообщения со статусом `pending` и публикует их в RabbitMQ. После успешной публикации статус сообщения меняется на `sent`.

### DLQ Consumer Worker

```bash
make start_dlq_consumer_worker
```

**Назначение:** Фоновый воркер, который потребляет сообщения из Dead Letter Queue (DLQ) — очереди недоставленных сообщений. Позволяет анализировать и повторно обрабатывать сообщения, которые не удалось доставить с первого раза.

---

## 9. Работа с Docker

### Запуск всех сервисов

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

### Остановка

```bash
docker compose -f infrastructure/docker-compose.yml down
```

### Сервисы

| Сервис                  | Контейнер                      | Описание                                   |
| ----------------------- | ------------------------------ | ------------------------------------------ |
| `postgres`              | `task_processor_postgres`      | PostgreSQL 14.5                            |
| `rabbitmq`              | `task_processor_rabbitmq`      | RabbitMQ 3.11 с Management UI (порт 15672) |
| `migration`             | `task_processor_migration`     | Однократный запуск миграций Alembic        |
| `app`                   | `task_processor_app`           | FastAPI приложение (uvicorn)               |
| `outbox-publish-worker` | `task_processor_outbox_worker` | Воркер публикации outbox                   |
| `dlq-consumer-worker`   | `task_processor_dlq_worker`    | Воркер обработки DLQ                       |

**Порядок запуска:**
1. `postgres` и `rabbitmq` запускаются параллельно
2. `migration` запускается после `postgres` (ждёт healthcheck)
3. `app`, `outbox-publish-worker`, `dlq-consumer-worker` запускаются после `migration` и `rabbitmq`

### Переменные окружения для Docker

Docker Compose использует переменные из `.env` файла в корне проекта. Убедитесь, что `.env` существует и содержит все необходимые переменные (см. раздел 2).

---

## 10. CI/CD пайплайн (GitHub Actions)

Пайплайн определён в файлах `.github/workflows/` и состоит из трёх последовательных этапов:

### Этап 1: Code Quality Check ([`.github/workflows/code-quality-check.yml`](.github/workflows/code-quality-check.yml))

Запускается на каждый push во все ветки.

- `black --check --diff .` — проверка форматирования
- `ruff check .` — линтинг
- `mypy .` — проверка типов

### Этап 2: Testing ([`.github/workflows/testing.yml`](.github/workflows/testing.yml))

Запускается после успешного прохождения code quality.

- **unit-tests** — `pytest -m unit` с coverage (без внешних сервисов)
- **integration-tests** — `pytest -m integration` с PostgreSQL (сервис GitHub Actions)
- **e2e-tests** — `pytest -m e2e` с PostgreSQL
- **coverage-combine** — объединение unit + integration coverage в единый отчёт

### Этап 3: SonarCloud ([`.github/workflows/sonarcloud.yml`](.github/workflows/sonarcloud.yml))

Запускается после успешного тестирования.

- Анализ кода с помощью SonarCloud
- Использует объединённый coverage-отчёт
- Требует `SONAR_TOKEN` в секретах репозитория

### Полный пайплайн ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))

```yaml
jobs:
  code-quality → testing → sonarcloud
```
