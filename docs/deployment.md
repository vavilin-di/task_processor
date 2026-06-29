# Инструкция по развёртыванию

---

## 1. Требования к окружению

| Компонент      | Версия | Назначение                             |
| -------------- | ------ | -------------------------------------- |
| Python         | 3.12   | Среда исполнения приложения            |
| PostgreSQL     | 14+    | Основная база данных                   |
| RabbitMQ       | 3.11+  | Брокер сообщений                       |
| Docker         | 24+    | Контейнеризация (рекомендуемый способ) |
| Docker Compose | 2.20+  | Оркестрация контейнеров                |
| uv             | 0.5+   | Пакетный менеджер (аналог pip/poetry)  |

---

## 2. Развёртывание через Docker Compose (рекомендуемый способ)

### 2.1. Подготовка

**Клонирование репозитория:**

```bash
git clone <url-репозитория>
cd task_processor
```

**Создание файла `.env`:**

Скопируйте шаблон и заполните переменные:

```bash
cp .env.example .env
```

#### Полная таблица переменных окружения

| Переменная                | Описание                                                             | Значение по умолчанию | Обязательная |
| ------------------------- | -------------------------------------------------------------------- | --------------------- | :----------: |
| **Общие настройки**       |
| `APP_ENV`                 | Окружение приложения (`development` / `production`)                  | `development`         |      Да      |
| `APP_TITLE`               | Название приложения                                                  | `task_processor`      |     Нет      |
| `APP_VERSION`             | Версия приложения                                                    | `0.1.0`               |     Нет      |
| `LOG_LEVEL`               | Уровень логирования                                                  | `INFO`                |     Нет      |
| `API_PREFIX`              | Префикс API                                                          | `/api`                |     Нет      |
| `API_VERSION_PREFIX`      | Префикс версии API                                                   | `/v1`                 |     Нет      |
| `ALLOWED_HOSTS`           | Список разрешённых хостов (через запятую)                            | `localhost,127.0.0.1` |     Нет      |
| `CORS_ORIGINS`            | Разрешённые CORS-источники (через запятую)                           | —                     |     Нет      |
| **PostgreSQL**            |
| `POSTGRES_HOST`           | Хост PostgreSQL                                                      | `localhost`           |      Да      |
| `POSTGRES_PORT`           | Порт PostgreSQL                                                      | `5432`                |      Да      |
| `POSTGRES_USER`           | Пользователь PostgreSQL                                              | `postgres`            |      Да      |
| `POSTGRES_PASSWORD`       | Пароль PostgreSQL                                                    | —                     |      Да      |
| `POSTGRES_DATABASE`       | Имя базы данных                                                      | `task_processor`      |      Да      |
| `POSTGRES_POOL_SIZE`      | Размер пула соединений                                               | `10`                  |     Нет      |
| `POSTGRES_MAX_OVERFLOW`   | Максимальное превышение пула                                         | `20`                  |     Нет      |
| `POSTGRES_POOL_TIMEOUT`   | Таймаут ожидания соединения (сек)                                    | `30`                  |     Нет      |
| `POSTGRES_POOL_RECYCLE`   | Пересоздание соединения (сек)                                        | `1800`                |     Нет      |
| **RabbitMQ**              |
| `RABBITMQ_HOST`           | Хост RabbitMQ                                                        | `localhost`           |      Да      |
| `RABBITMQ_PORT`           | Порт RabbitMQ (AMQP)                                                 | `5672`                |      Да      |
| `RABBITMQ_USER`           | Пользователь RabbitMQ                                                | `guest`               |      Да      |
| `RABBITMQ_PASSWORD`       | Пароль RabbitMQ                                                      | —                     |      Да      |
| `RABBITMQ_VIRTUAL_HOST`   | Virtual host RabbitMQ                                                | `/`                   |     Нет      |
| `RABBITMQ_PREFETCH_COUNT` | Prefetch count (количество сообщений, выдаваемых потребителю за раз) | `10`                  |     Нет      |
| `RABBITMQ_HEARTBEAT`      | Интервал heartbeat (сек)                                             | `60`                  |     Нет      |

### 2.2. Запуск

> **Важно:** Файл `docker-compose.yml` находится в директории `infrastructure/`, а файл `.env` — в корне проекта.
> При запуске необходимо указывать путь к `.env` через флаг `--env-file`, иначе переменные окружения не будут подставлены.

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env up -d
```

**Порядок запуска сервисов:**

1. **postgres** — запуск СУБД, ожидание готовности через `pg_isready`
2. **rabbitmq** — запуск брокера, ожидание готовности через `rabbitmq-diagnostics check_port_connectivity`
3. **migration** — применение миграций Alembic. Это **однократная задача**: контейнер запускается, применяет миграции и завершается со статусом `Exited (0)`. Это **нормальное поведение**, не ошибка.
4. **app** — FastAPI-приложение (зависит от migration и rabbitmq)
5. **outbox-publish-worker** — воркер публикации outbox-сообщений (зависит от migration и rabbitmq)
6. **dlq-consumer-worker** — воркер обработки DLQ-сообщений (зависит от migration и rabbitmq)

**Healthcheck:**

- **PostgreSQL:** `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DATABASE}` (интервал 5s, 5 ретраев)
- **RabbitMQ:** `rabbitmq-diagnostics check_port_connectivity` (интервал 10s, 5 ретраев)

### 2.3. Сервисы

| Сервис                  | Контейнер                      | Порты (хост:контейнер)                                     | Зависимости         |
| ----------------------- | ------------------------------ | ---------------------------------------------------------- | ------------------- |
| `postgres`              | `task_processor_postgres`      | `127.0.0.1:5432:${POSTGRES_PORT}`                          | —                   |
| `rabbitmq`              | `task_processor_rabbitmq`      | `127.0.0.1:5672:${RABBITMQ_PORT}`, `127.0.0.1:15672:15672` | —                   |
| `migration`             | `task_processor_migration`     | —                                                          | postgres (healthy)  |
| `app`                   | `task_processor_app`           | `127.0.0.1:8000:8000`                                      | migration, rabbitmq |
| `outbox-publish-worker` | `task_processor_outbox_worker` | —                                                          | migration, rabbitmq |
| `dlq-consumer-worker`   | `task_processor_dlq_worker`    | —                                                          | migration, rabbitmq |

### 2.4. Проверка

**Статус контейнеров:**

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env ps
```

**Health check приложения:**

```bash
curl http://localhost:8000/api/v1/tasks
```

Ожидаемый ответ — пустой массив `[]` или список задач (HTTP 200).

**Логи приложения:**

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env logs -f app
```

**Логи любого сервиса:**

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env logs -f <service_name>
```

### 2.5. Остановка

**Остановка сервисов (тома сохраняются):**

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env down
```

**Полная остановка с удалением томов (БД и данные RabbitMQ будут стёрты):**

```bash
docker compose -f infrastructure/docker-compose.yml --env-file .env down -v
```

---

## 3. Развёртывание без Docker

### 3.1. Установка зависимостей

Убедитесь, что установлен [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Команда установит все зависимости, включая dev-зависимости для разработки.

### 3.2. Настройка .env

Создайте файл `.env` в корне проекта. Ключевые отличия от Docker-развёртывания:

```ini
# Общие настройки
APP_ENV=development
LOG_LEVEL=INFO

# PostgreSQL — хост localhost, а не имя контейнера
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=task_processor
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=20
POSTGRES_POOL_TIMEOUT=30
POSTGRES_POOL_RECYCLE=1800

# RabbitMQ — хост localhost, а не имя контейнера
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VIRTUAL_HOST=/
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_HEARTBEAT=60
```

### 3.3. Применение миграций

```bash
make migrate
```

Или напрямую:

```bash
uv run alembic upgrade head
```

### 3.4. Запуск сервисов

Запускайте каждый сервис в отдельном терминале.

**FastAPI-приложение:**

```bash
make start_main_app
```

По умолчанию: хост `127.0.0.1`, порт `8080`, 1 worker. Параметры можно переопределить:

```bash
make start_main_app HOST=0.0.0.0 PORT=8000 WORKERS_COUNT=4
```

**Outbox Publisher Worker:**

```bash
make start_outbox_publish_worker
```

**DLQ Consumer Worker:**

```bash
make start_dlq_consumer_worker
```

---

## 4. Production-рекомендации

### 4.1. FastAPI

- Используйте production ASGI-сервер — **uvicorn с несколькими workers**.
- Запуск: `make start_main_app` с `WORKERS_COUNT >= 2`.
- Настройте reverse proxy (nginx, Caddy) для терминирования TLS и балансировки.
- Установите `APP_ENV=production` — это отключит debug-режим.
- Ограничьте `ALLOWED_HOSTS` и `CORS_ORIGINS`.

### 4.2. PostgreSQL

- Настройте параметры пула соединений под нагрузку:
  - `POSTGRES_POOL_SIZE` — базовый размер пула (рекомендуется: 10–50)
  - `POSTGRES_MAX_OVERFLOW` — максимальное превышение (рекомендуется: 20–100)
  - `POSTGRES_POOL_TIMEOUT` — таймаут ожидания соединения (рекомендуется: 30–60 сек)
  - `POSTGRES_POOL_RECYCLE` — пересоздание соединения (рекомендуется: 1800–3600 сек)
- Настройте регулярные бэкапы (pg_dump / pgBackRest).
- Мониторинг активных соединений: `SELECT * FROM pg_stat_activity WHERE datname = 'task_processor';`

### 4.3. RabbitMQ

- Настройте `RABBITMQ_PREFETCH_COUNT` под производительность обработчиков (рекомендуется: 10–50).
- Настройте `RABBITMQ_HEARTBEAT` для обнаружения разрывов соединения (рекомендуется: 60 сек).
- Используйте Management UI для мониторинга: `http://host:15672` (логин/пароль из `RABBITMQ_USER` / `RABBITMQ_PASSWORD`).
- Отслеживайте очереди:
  - `task_processing` — основные задачи
  - `task_processing_dlq` — упавшие сообщения (Dead Letter Queue)

### 4.4. Outbox Worker

- Убедитесь, что запущен **ровно 1 экземпляр** воркера. Механизм `FOR UPDATE SKIP LOCKED` позволяет запустить несколько, но для production достаточно одного.
- Мониторинг неопубликованных сообщений:

  ```sql
  SELECT COUNT(*) FROM outbox_messages WHERE is_published = false AND is_failed = false;
  ```

- Мониторинг упавших сообщений:

  ```sql
  SELECT COUNT(*) FROM outbox_messages WHERE is_failed = true;
  ```

### 4.5. DLQ Consumer Worker

- Воркер должен быть запущен постоянно для обработки упавших сообщений из DLQ.
- Мониторинг количества сообщений в DLQ:

  ```sql
  SELECT COUNT(*) FROM dlq_messages;
  ```

---

## 5. CI/CD (GitHub Actions)

Проект содержит три workflow в директории [`.github/workflows/`](../.github/workflows/):

| Workflow               | Файл                                                                    | Назначение                                              |
| ---------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------- |
| **Code Quality Check** | [`code-quality-check.yml`](../.github/workflows/code-quality-check.yml) | Линтинг: black, ruff, mypy                              |
| **Testing**            | [`testing.yml`](../.github/workflows/testing.yml)                       | Unit, интеграционные (с PostgreSQL service) и e2e-тесты |
| **SonarCloud**         | [`sonarcloud.yml`](../.github/workflows/sonarcloud.yml)                 | Анализ кода с покрытием                                 |

Все workflow вызываются через `workflow_call` и могут быть частью общего пайплайна.

---

## 6. Мониторинг

### RabbitMQ Management UI

```
http://<host>:15672
```

Логин и пароль — из переменных `RABBITMQ_USER` и `RABBITMQ_PASSWORD`.

### Логи сервисов

```bash
docker compose -f infrastructure/docker-compose.yml logs -f <service_name>
```

### SQL-запросы для мониторинга

**Неопубликованные outbox-сообщения:**

```sql
SELECT COUNT(*) FROM outbox_messages WHERE is_published = false AND is_failed = false;
```

**Упавшие outbox-сообщения:**

```sql
SELECT COUNT(*) FROM outbox_messages WHERE is_failed = true;
```

**Последние сообщения в DLQ:**

```sql
SELECT * FROM dlq_messages ORDER BY created_at DESC LIMIT 10;
```

**Активные задачи:**

```sql
SELECT COUNT(*) FROM tasks WHERE is_active = true;
```

---

## 7. Безопасность

- **Пароли и секреты** хранятся только в `.env` и **не попадают в код**.
- **Pydantic `SecretStr`** используется для защиты паролей в настройках — при выводе в логи пароль маскируется.
- **CORS** ограничен через переменную `CORS_ORIGINS`.
- **ALLOWED_HOSTS** валидирует заголовок `Host` входящих запросов.
- **Порты БД и RabbitMQ** привязаны к `127.0.0.1` (localhost) — сервисы недоступны извне.
- **Dockerfile:** приложение запускается от пользователя `app` (не root).
- **Регулярно обновляйте зависимости** через `uv sync --upgrade` и проверяйте уязвимости.

---

## 8. Решение проблем при развёртывании

| Проблема                        | Диагностика                                                 | Решение                                                         |
| ------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| Контейнер не стартует           | `docker compose logs <service>`                             | Проверить ошибки в логах                                        |
| Ошибка подключения к БД         | Проверить `POSTGRES_*` переменные                           | Убедиться, что postgres healthy: `docker compose logs postgres` |
| Ошибка подключения к RabbitMQ   | Проверить `RABBITMQ_*` переменные                           | Убедиться, что rabbitmq healthy: `docker compose logs rabbitmq` |
| Миграции не применились         | `docker compose logs migration`                             | Проверить код ошибки в логах migration                          |
| 502 Bad Gateway                 | Проверить логи app                                          | Возможно, не хватает workers — увеличьте `WORKERS_COUNT`        |
| Outbox-сообщения не публикуются | Проверить outbox-publish-worker и таблицу `outbox_messages` | Убедиться, что воркер запущен и RabbitMQ доступен               |
| DLQ-сообщения не обрабатываются | Проверить dlq-consumer-worker                               | Убедиться, что воркер запущен и RabbitMQ доступен               |