# Инструкция администратора

## async-task-manager

Асинхронный сервис управления задачами на FastAPI + RabbitMQ + PostgreSQL с паттерном Outbox.

---

## 1. Требования к окружению

| Компонент      | Версия              |
| -------------- | ------------------- |
| Python         | 3.12                |
| PostgreSQL     | 14+                 |
| RabbitMQ       | 3.11+               |
| uv             | последняя           |
| Docker         | 24+ (опционально)   |
| Docker Compose | 2.20+ (опционально) |

---

## 2. Установка и настройка

### 2.1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd task_processor
```

### 2.2. Файл `.env`

Создайте файл `.env` в корне проекта. Шаблон:

```bash
cp .env.example .env
```

#### Переменные окружения

| Переменная                | По умолчанию                 | Описание                                                 |
| ------------------------- | ---------------------------- | -------------------------------------------------------- |
| `APP_ENV`                 | `development`                | Окружение: `development` / `production`                  |
| `LOG_LEVEL`               | `INFO`                       | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ALLOWED_HOSTS`           | `["localhost", "127.0.0.1"]` | Белый список разрешённых хостов                          |
| `CORS_ORIGINS`            | `[]`                         | Разрешённые CORS-источники (список URL)                  |
| `POSTGRES_HOST`           | —                            | Хост PostgreSQL                                          |
| `POSTGRES_PORT`           | `5432`                       | Порт PostgreSQL                                          |
| `POSTGRES_USER`           | —                            | Пользователь PostgreSQL                                  |
| `POSTGRES_PASSWORD`       | —                            | Пароль PostgreSQL (SecretStr — не выводится в логах)     |
| `POSTGRES_DATABASE`       | —                            | Имя базы данных                                          |
| `POSTGRES_POOL_SIZE`      | `10`                         | Размер пула соединений                                   |
| `POSTGRES_MAX_OVERFLOW`   | `20`                         | Максимальное количество соединений сверх пула            |
| `POSTGRES_POOL_TIMEOUT`   | `30`                         | Таймаут ожидания соединения из пула (сек)                |
| `POSTGRES_POOL_RECYCLE`   | `1800`                       | Время переиспользования соединения (сек)                 |
| `RABBITMQ_HOST`           | —                            | Хост RabbitMQ                                            |
| `RABBITMQ_PORT`           | `5672`                       | Порт RabbitMQ (AMQP)                                     |
| `RABBITMQ_USER`           | —                            | Пользователь RabbitMQ                                    |
| `RABBITMQ_PASSWORD`       | —                            | Пароль RabbitMQ (SecretStr — не выводится в логах)       |
| `RABBITMQ_VIRTUAL_HOST`   | `/`                          | Virtual host RabbitMQ                                    |
| `RABBITMQ_PREFETCH_COUNT` | `10`                         | Количество сообщений, получаемых за раз                  |
| `RABBITMQ_HEARTBEAT`      | `60`                         | Интервал heartbeat (сек)                                 |

### 2.3. Установка зависимостей

**Локально (через uv):**

```bash
make install
```

Эта команда выполнит `uv sync` и применит миграции.

**Через Docker Compose:**

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

### 2.4. Применение миграций

```bash
make migrate
# или
uv run alembic upgrade head
```

---

## 3. Запуск сервисов

### 3.1. Основное приложение (FastAPI)

**Режим разработки** (с авто-перезагрузкой):

```bash
make dev
# HOST=127.0.0.1 PORT=8080 --reload
```

**Production-запуск:**

```bash
make start_main_app
# HOST=127.0.0.1 PORT=8080 WORKERS_COUNT=1
```

С переменными:

```bash
make start_main_app HOST=0.0.0.0 PORT=8000 WORKERS_COUNT=4
```

**Напрямую через Uvicorn:**

```bash
uv run uvicorn src:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3.2. Outbox Publisher Worker

```bash
make start_outbox_publish_worker
```

**Назначение:** фоновый воркер, который периодически опрашивает таблицу [`outbox_messages`](src/database/models/outbox_messages.py) и публикует неопубликованные сообщения в RabbitMQ.

- Интервал опроса: **0.5 секунды** (настраивается в коде: [`run_outbox_publish_worker`](src/workers/outbox_publisher/outbox_publish_worker.py:14), параметр `poll_interval`)
- За одну итерацию обрабатывается до 10 сообщений (параметр `limit` в [`publish_batch`](src/services/outbox_messages.py:21))

### 3.3. DLQ Consumer Worker

```bash
make start_dlq_consumer_worker
```

**Назначение:** слушает DLQ-очередь [`task_processing_dlq`](src/messaging/queues.py:31) и выполняет повторные попытки обработки сообщений.

- Максимальное количество повторов: **3**
- Задержки между повторами: **5, 10, 15 секунд** (настраивается в [`dlq_consumer_worker.py`](src/workers/dlq_consumer/dlq_consumer_worker.py:18))
- После исчерпания попыток — запись в таблицу [`dlq_messages`](src/database/models/dlq_messages.py) в БД

---

## 4. Docker Compose

### 4.1. Состав сервисов

| Сервис                  | Контейнер                      | Образ / Команда                                                                             | Порты                                                      | Зависимости                       |
| ----------------------- | ------------------------------ | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------- |
| `postgres`              | `task_processor_postgres`      | `postgres:14.5`                                                                             | `127.0.0.1:5432:${POSTGRES_PORT}`                          | —                                 |
| `rabbitmq`              | `task_processor_rabbitmq`      | `rabbitmq:3.11-management`                                                                  | `127.0.0.1:5672:${RABBITMQ_PORT}`, `127.0.0.1:15672:15672` | —                                 |
| `migration`             | `task_processor_migration`     | сборка из `infrastructure/Dockerfile`, команда `alembic upgrade head`                       | —                                                          | `postgres` (healthy)              |
| `app`                   | `task_processor_app`           | сборка из `infrastructure/Dockerfile`, команда `uvicorn src:app --host 0.0.0.0 --port 8000` | `127.0.0.1:8000:8000`                                      | `migration`, `rabbitmq` (healthy) |
| `outbox-publish-worker` | `task_processor_outbox_worker` | сборка из `infrastructure/Dockerfile`, команда `run_outbox_publish_worker`                  | —                                                          | `migration`, `rabbitmq` (healthy) |
| `dlq-consumer-worker`   | `task_processor_dlq_worker`    | сборка из `infrastructure/Dockerfile`, команда `run_dlq_consumer_worker`                    | —                                                          | `migration`, `rabbitmq` (healthy) |

**Healthcheck:**

- **PostgreSQL:** `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DATABASE}` (интервал 5 сек, 5 попыток)
- **RabbitMQ:** `rabbitmq-diagnostics check_port_connectivity` (интервал 10 сек, 5 попыток)

### 4.2. Команды управления

```bash
# Запуск всех сервисов
docker compose -f infrastructure/docker-compose.yml up -d

# Остановка всех сервисов
docker compose -f infrastructure/docker-compose.yml down

# Просмотр логов конкретного сервиса
docker compose -f infrastructure/docker-compose.yml logs -f app
docker compose -f infrastructure/docker-compose.yml logs -f outbox-publish-worker
docker compose -f infrastructure/docker-compose.yml logs -f dlq-consumer-worker

# Перезапуск воркера
docker compose -f infrastructure/docker-compose.yml restart outbox-publish-worker

# Просмотр состояния
docker compose -f infrastructure/docker-compose.yml ps
```

---

## 5. Мониторинг и логирование

### 5.1. RabbitMQ Management UI

- **URL:** http://localhost:15672
- **Логин:** значение `RABBITMQ_USER` из `.env`
- **Пароль:** значение `RABBITMQ_PASSWORD` из `.env`

Через веб-интерфейс можно отслеживать:
- состояние очередей (`task_processing`, `task_processing_dlq`);
- количество сообщений в очереди;
- количество подтверждённых/отклонённых сообщений;
- подключения и каналы.

### 5.2. Логи приложения

**Через Docker:**

```bash
docker compose -f infrastructure/docker-compose.yml logs -f app
docker compose -f infrastructure/docker-compose.yml logs -f outbox-publish-worker
docker compose -f infrastructure/docker-compose.yml logs -f dlq-consumer-worker
```

**Локально:** логи выводятся в stdout терминала, в котором запущен процесс.

### 5.3. Уровень логирования

Настраивается через переменную `LOG_LEVEL` в `.env`:

| Значение  | Описание                                     |
| --------- | -------------------------------------------- |
| `DEBUG`   | Подробное логирование (все запросы, отладка) |
| `INFO`    | Стандартное логирование (по умолчанию)       |
| `WARNING` | Только предупреждения и ошибки               |
| `ERROR`   | Только ошибки                                |

---

## 6. Обслуживание базы данных

### 6.1. Миграции

```bash
# Применить все миграции
make migrate
# или
uv run alembic upgrade head

# Создать новую миграцию (на основе изменений в моделях)
uv run alembic revision --autogenerate -m "описание изменений"

# Откатить последнюю миграцию
uv run alembic downgrade -1

# Откатить до конкретной ревизии
uv run alembic downgrade <revision_id>
```

### 6.2. Проверка моделей

```bash
make check_models
# или
uv run alembic check
```

Проверяет, что текущее состояние моделей SQLAlchemy соответствует последней миграции.

### 6.3. PostgreSQL healthcheck

```bash
pg_isready -U <POSTGRES_USER> -d <POSTGRES_DATABASE>
```

---

## 7. Dead Letter Queue (DLQ)

### 7.1. Описание

Сообщения, не обработанные за **TTL = 10 минут** (600 000 мс), автоматически перемещаются из основной очереди `task_processing` в DLQ-очередь `task_processing_dlq`.

Механизм основан на настройках очереди (см. [`queues.py`](src/messaging/queues.py:20)):

- `x-dead-letter-exchange`: `tasks_dlx`
- `x-dead-letter-routing-key`: `failed`
- `x-message-ttl`: `600000` (10 минут)
- `x-max-length`: `10000` (максимум сообщений в очереди)

### 7.2. Обработка DLQ Consumer Worker

Воркер [`DLQConsumerWorker`](src/workers/dlq_consumer/dlq_consumer_worker.py:24) автоматически обрабатывает DLQ:

1. Получает сообщение из очереди `task_processing_dlq`
2. Проверяет количество предыдущих попыток (через заголовок `x-death`)
3. Если попыток **меньше 3** — публикует сообщение в retry-очередь с задержкой:
   - 1-я попытка: задержка **5 секунд**
   - 2-я попытка: задержка **10 секунд**
   - 3-я попытка: задержка **15 секунд**
4. Если попыток **3 и более** — записывает сообщение в таблицу [`dlq_messages`](src/database/models/dlq_messages.py) в БД

### 7.3. Просмотр DLQ-сообщений в БД

```sql
SELECT * FROM dlq_messages;
```

Структура таблицы:

| Колонка                | Тип            | Описание                       |
| ---------------------- | -------------- | ------------------------------ |
| `id`                   | `INTEGER`      | Первичный ключ                 |
| `original_routing_key` | `VARCHAR(255)` | Оригинальный routing key       |
| `original_payload`     | `JSON`         | Исходное тело сообщения        |
| `error_type`           | `VARCHAR(255)` | Тип ошибки                     |
| `error_message`        | `TEXT`         | Текст ошибки                   |
| `retry_count`          | `INTEGER`      | Количество выполненных попыток |
| `x_death`              | `JSON`         | Заголовки x-death из RabbitMQ  |
| `created_at`           | `DATETIME`     | Время записи                   |

### 7.4. Ручной повтор DLQ-сообщений

Можно извлечь сообщение из таблицы `dlq_messages` и опубликовать заново в основную очередь:

```sql
SELECT original_payload FROM dlq_messages WHERE id = <id>;
```

Затем вручную опубликовать через RabbitMQ Management UI (вкладка **Queues** → `task_processing` → **Publish message**) или через CLI.

---

## 8. Outbox Pattern

### 8.1. Описание

Паттерн Outbox обеспечивает **гарантированную доставку** сообщений в RabbitMQ. При создании задачи в одной транзакции создаются две записи:

- запись в таблице [`tasks`](src/database/models/tasks.py);
- запись в таблице [`outbox_messages`](src/database/models/outbox_messages.py) с `is_published = false`.

### 8.2. Процесс публикации

1. **Создание задачи** — в рамках одной транзакции создаётся задача и outbox-сообщение.
2. **Outbox Publisher Worker** — фоновый воркер периодически опрашивает таблицу `outbox_messages` и публикует неопубликованные сообщения в RabbitMQ.
3. **Отметка о публикации** — после успешной публикации сообщение помечается `is_published = true`.
4. **Ошибки публикации** — при ошибке текст ошибки добавляется в массив `errors`. После **5 ошибок** поле `is_failed` устанавливается в `true`.

### 8.3. Мониторинг outbox

```sql
-- Количество неопубликованных сообщений (ожидают отправки)
SELECT COUNT(*) FROM outbox_messages WHERE is_published = false AND is_failed = false;

-- Количество упавших сообщений (требуют ручного вмешательства)
SELECT COUNT(*) FROM outbox_messages WHERE is_failed = true;

-- Детальный просмотр неопубликованных
SELECT id, aggregate_id, routing_key, created_at, errors
FROM outbox_messages
WHERE is_published = false AND is_failed = false
ORDER BY created_at;
```

Структура таблицы [`outbox_messages`](src/database/models/outbox_messages.py):

| Колонка        | Тип                       | Описание                        |
| -------------- | ------------------------- | ------------------------------- |
| `id`           | `INTEGER`                 | Первичный ключ                  |
| `aggregate_id` | `INTEGER` (FK → tasks.id) | ID задачи, CASCADE при удалении |
| `routing_key`  | `VARCHAR(255)`            | Routing key для RabbitMQ        |
| `payload`      | `JSON`                    | Тело сообщения                  |
| `is_published` | `BOOLEAN`                 | Флаг публикации                 |
| `is_failed`    | `BOOLEAN`                 | Флаг ошибки (после 5 ошибок)    |
| `created_at`   | `DATETIME`                | Время создания                  |
| `errors`       | `ARRAY[STRING]`           | Массив ошибок публикации        |

Индекс: `outbox_messages_not_published_idx` по `created_at` с условием `is_published = false AND is_failed = false`.

---

## 9. Health Check

### 9.1. Эндпоинт приложения

```
GET /api/v1/tasks
```

Если эндпоинт отвечает статусом `200 OK` — приложение живо и работает.

### 9.2. Docker healthcheck

- **PostgreSQL:** `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DATABASE}`
- **RabbitMQ:** `rabbitmq-diagnostics check_port_connectivity`

---

## 10. Безопасность

### 10.1. Пароли

- Все пароли хранятся в файле `.env`
- Пароли PostgreSQL и RabbitMQ используют тип [`SecretStr`](src/settings/postgres.py:15) из Pydantic — они **не выводятся в логах** и при сериализации

### 10.2. CORS

Настраивается через переменную `CORS_ORIGINS` в `.env`. Принимает список разрешённых источников (AnyHttpUrl).

### 10.3. ALLOWED_HOSTS

Переменная `ALLOWED_HOSTS` задаёт белый список хостов, с которых разрешены запросы к API.

### 10.4. Привязка портов к localhost

В Docker Compose критически важные порты привязаны к `127.0.0.1`:

- **RabbitMQ Management UI** (`15672`) — только localhost
- **PostgreSQL** (`5432`) — только localhost
- **FastAPI** (`8000`) — только localhost

### 10.5. Dockerfile

Запуск от непривилегированного пользователя:

```dockerfile
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app && \
    chown -R app:app /app
USER app
```

См. [`infrastructure/Dockerfile`](infrastructure/Dockerfile:21).

---

## 11. Решение проблем

### 11.1. Ошибка подключения к БД

**Симптом:** приложение не стартует, в логах `could not connect to server`.

**Проверка:**
- Корректность переменных `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE` в `.env`
- Запущен ли PostgreSQL: `docker compose ps` или `pg_isready`
- Доступность хоста: `ping <POSTGRES_HOST>`

### 11.2. Ошибка подключения к RabbitMQ

**Симптом:** воркеры не стартуют, в логах `connection refused`.

**Проверка:**
- Корректность переменных `RABBITMQ_HOST`, `RABBITMQ_PORT`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` в `.env`
- Запущен ли RabbitMQ: `docker compose ps`
- Доступность Management UI: http://localhost:15672

### 11.3. Сообщения не публикуются

**Симптом:** задачи создаются, но не обрабатываются.

**Проверка:**
- Запущен ли `outbox-publish-worker`: `docker compose ps`
- Логи воркера: `docker compose logs -f outbox-publish-worker`
- Наличие неопубликованных сообщений:
  ```sql
  SELECT COUNT(*) FROM outbox_messages WHERE is_published = false AND is_failed = false;
  ```
- Если сообщения есть, но воркер работает — проверить подключение к RabbitMQ

### 11.4. Сообщения в DLQ

**Симптом:** задачи не обрабатываются, сообщения уходят в DLQ.

**Проверка:**
- Запущен ли `dlq-consumer-worker`: `docker compose ps`
- Логи воркера: `docker compose logs -f dlq-consumer-worker`
- Просмотр DLQ-сообщений в БД:
  ```sql
  SELECT * FROM dlq_messages ORDER BY created_at DESC LIMIT 10;
  ```
- Если воркер не справляется — проверить RabbitMQ Management UI (очередь `task_processing_dlq`)

### 11.5. 409 Conflict

**Симптом:** при запросе возвращается `409 Conflict`.

**Причина:** `IntegrityError` — связанная запись была удалена (например, задача удалена, а outbox-сообщение осталось, но FK настроен на `ON DELETE CASCADE`).

**Решение:** проверить целостность данных, убедиться, что каскадное удаление отработало.

### 11.6. 404 Not Found

**Симптом:** при запросе задачи возвращается `404 Not Found`.

**Причина:** задача не найдена. Возможные причины:
- Задача была удалена (soft-delete: `is_active = false`)
- Задача с указанным ID не существует

**Проверка:**
```sql
SELECT id, name, is_active FROM tasks WHERE id = <id>;