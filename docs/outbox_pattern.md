# Transactional Outbox Pattern

## Реализация в проекте

### Модель OutboxMessage

Модель SQLAlchemy для таблицы `outbox_messages`:

- **Таблица:** `outbox_messages`
- **Поля:**
  - `id` — первичный ключ (SERIAL)
  - `aggregate_id` — внешний ключ на `tasks(id)` с `ON DELETE CASCADE`
  - `routing_key` — ключ маршрутизации для RabbitMQ (например, `tasks.create`)
  - `payload` — тело сообщения в формате JSON
  - `is_published` — флаг успешной публикации (по умолчанию `false`)
  - `is_failed` — флаг, что сообщение упало после превышения лимита ошибок (по умолчанию `false`)
  - `created_at` — временная метка создания
  - `errors` — массив строк с описанием ошибок публикации

**Partial index:** `outbox_messages_not_published_idx` на `created_at` с условием `WHERE is_published = false AND is_failed = false`.

**Ссылка:** [`src/database/models/outbox_messages.py`](src/database/models/outbox_messages.py)

---

### Создание outbox-сообщения

В сервисе задач [`src/services/tasks.py`](src/services/tasks.py) метод `create_task` создаёт задачу и outbox-сообщение в одной транзакции:

1. Начинается транзакция БД.
2. Создаётся запись `Task`.
3. Создаётся запись `OutboxMessage`:
   - `routing_key = "tasks.create"`
   - `aggregate_id = task.id`
   - `payload = task.payload` (сериализованные данные задачи)
4. Транзакция коммитится.

Если на любом из этапов происходит ошибка — транзакция откатывается, и сообщение не сохраняется.

---

### OutboxMessageRepository

Репозиторий [`src/repositories/outbox_messages.py`](src/repositories/outbox_messages.py) предоставляет методы для работы с outbox-сообщениями:

- **`get_not_published_outbox_messages(limit=10)`**
  - Выполняет `SELECT ... FOR UPDATE SKIP LOCKED` с сортировкой по `created_at ASC`.
  - Использует streaming-результаты для экономии памяти.
  - Возвращает только сообщения, где `is_published = false` и `is_failed = false`.

- **`mark_messages_as_published(message_ids)`**
  - Выполняет batch-обновление: `UPDATE outbox_messages SET is_published = true WHERE id IN (...)`

- **`add_error(task_id, error)`**
  - Добавляет ошибку в массив `errors` через `array_append`.
  - Если количество ошибок достигло `MAX_PUBLISH_ERRORS_COUNT = 5`, устанавливает `is_failed = true`.

---

### OutboxMessageService

Сервис [`src/services/outbox_messages.py`](src/services/outbox_messages.py) содержит бизнес-логику публикации сообщений:

**Метод `publish_batch(limit=10)`:**

1. Получает неопубликованные сообщения через репозиторий (с блокировкой `FOR UPDATE SKIP LOCKED`).
2. Для каждого сообщения:
   - Публикует в RabbitMQ в очередь `TASKS_QUEUE` с указанным `routing_key`.
   - При успехе: добавляет ID сообщения в список опубликованных.
   - При ошибке: логирует ошибку, вызывает `add_error` для записи в БД.
3. После завершения цикла: вызывает `mark_messages_as_published` для batch-обновления успешно опубликованных сообщений.

---

### Outbox Publisher Worker

Фоновый воркер [`src/workers/outbox_publisher/outbox_publish_worker.py`](src/workers/outbox_publisher/outbox_publish_worker.py):

- Запускает бесконечный цикл с интервалом опроса `poll_interval = 0.5` секунды.
- На каждой итерации:
  1. Получает контейнер зависимостей через Dishka.
  2. Вызывает `OutboxMessageService.publish_batch()`.
  3. Ожидает `poll_interval` перед следующей итерацией.

Точка входа: [`src/workers/outbox_publisher/run_outbox_publish_worker.py`](src/workers/outbox_publisher/run_outbox_publish_worker.py)