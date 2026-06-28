# API Документация — Async Task Manager

**Базовый URL:** `/api/v1`

---

## Эндпоинты

### POST `/api/v1/tasks` — Создать задачу

Создаёт задачу и outbox-сообщение в одной транзакции.

**Статус ответа:** `201 Created`

**Тело запроса (`TaskCreate`):**

```json
{
  "name": "string",
  "description": "string",
  "priority": "Средний",
  "payload": {}
}
```

- `priority` — enum: `"Низкий"`, `"Средний"`, `"Высокий"`

**Тело ответа (`Task`):**

```json
{
  "id": 1,
  "name": "string",
  "description": "string",
  "priority": "Средний",
  "status": "Новая задача",
  "created_at": "2024-01-01T00:00:00",
  "started_at": null,
  "finished_at": null,
  "result": null,
  "errors": null,
  "is_active": true
}
```

**Ошибки:**

| Код                    | Описание                           |
| ---------------------- | ---------------------------------- |
| `409 Conflict`         | `IntegrityError` — конфликт данных |
| `422 Validation Error` | Ошибка Pydantic-валидации          |

---

### GET `/api/v1/tasks` — Список задач

Курсорная пагинация через `sqlakeyset`, фильтрация по полям с суффиксами `_from` / `_to` для диапазонов.

**Статус ответа:** `200 OK`

**Параметры запроса (query):**

| Параметр           | Тип        | Обязательный | По умолчанию | Описание                       |
| ------------------ | ---------- | ------------ | ------------ | ------------------------------ |
| `cursor`           | `str`      | нет          | —            | Курсор для пагинации           |
| `limit`            | `int`      | нет          | `20`         | Количество записей на странице |
| `name`             | `str`      | нет          | —            | Фильтр по имени                |
| `description`      | `str`      | нет          | —            | Фильтр по описанию             |
| `priority`         | `str`      | нет          | —            | Фильтр по приоритету           |
| `status`           | `str`      | нет          | —            | Фильтр по статусу              |
| `created_at_from`  | `datetime` | нет          | —            | Фильтр по дате создания (>=)   |
| `created_at_to`    | `datetime` | нет          | —            | Фильтр по дате создания (<=)   |
| `started_at_from`  | `datetime` | нет          | —            | Фильтр по дате начала (>=)     |
| `started_at_to`    | `datetime` | нет          | —            | Фильтр по дате начала (<=)     |
| `finished_at_from` | `datetime` | нет          | —            | Фильтр по дате завершения (>=) |
| `finished_at_to`   | `datetime` | нет          | —            | Фильтр по дате завершения (<=) |

**Тело ответа (`PaginatedResponse[Task]`):**

```json
{
  "items": [
    {
      "id": 1,
      "name": "string",
      "description": "string",
      "priority": "Средний",
      "status": "Новая задача",
      "created_at": "2024-01-01T00:00:00",
      "started_at": null,
      "finished_at": null,
      "result": null,
      "errors": null,
      "is_active": true
    }
  ],
  "next_cursor": "string",
  "has_next": true
}
```

**Ошибки:**

| Код                    | Описание                  |
| ---------------------- | ------------------------- |
| `422 Validation Error` | Ошибка Pydantic-валидации |

---

### GET `/api/v1/tasks/{task_id}` — Получить задачу

**Статус ответа:** `200 OK` / `404 Not Found`

**Параметры пути:**

| Параметр  | Тип   | Обязательный | Описание  |
| --------- | ----- | ------------ | --------- |
| `task_id` | `int` | да           | ID задачи |

**Тело ответа:** `Task`

**Ошибки:**

| Код             | Описание          |
| --------------- | ----------------- |
| `404 Not Found` | Задача не найдена |

---

### DELETE `/api/v1/tasks/{task_id}` — Отменить задачу

Soft-delete: `UPDATE is_active = false, status = CANCELLED`.

**Статус ответа:** `200 OK` / `404 Not Found`

**Параметры пути:**

| Параметр  | Тип   | Обязательный | Описание  |
| --------- | ----- | ------------ | --------- |
| `task_id` | `int` | да           | ID задачи |

**Тело ответа:** `Task` (со статусом `"Отменена"`)

**Ошибки:**

| Код             | Описание          |
| --------------- | ----------------- |
| `404 Not Found` | Задача не найдена |

---

### GET `/api/v1/tasks/{task_id}/status` — Получить статус задачи

**Статус ответа:** `200 OK` / `404 Not Found`

**Параметры пути:**

| Параметр  | Тип   | Обязательный | Описание  |
| --------- | ----- | ------------ | --------- |
| `task_id` | `int` | да           | ID задачи |

**Тело ответа:** строка со статусом (например, `"Новая задача"`)

**Ошибки:**

| Код             | Описание          |
| --------------- | ----------------- |
| `404 Not Found` | Задача не найдена |

---

## Модели данных (Pydantic схемы)

### `TaskCreate`

| Поле          | Тип              | Обязательное | По умолчанию |
| ------------- | ---------------- | ------------ | ------------ |
| `name`        | `str`            | да           | —            |
| `description` | `str`            | да           | —            |
| `priority`    | `TaskPriority`   | нет          | `"Средний"`  |
| `payload`     | `dict[str, Any]` | да           | —            |

### `Task`

| Поле          | Тип                 | Описание              |
| ------------- | ------------------- | --------------------- |
| `id`          | `int`               | ID задачи             |
| `name`        | `str`               | Название              |
| `description` | `str`               | Описание              |
| `priority`    | `TaskPriority`      | Приоритет             |
| `status`      | `TaskStatus`        | Статус                |
| `created_at`  | `datetime`          | Дата создания         |
| `started_at`  | `datetime \| None`  | Дата начала           |
| `finished_at` | `datetime \| None`  | Дата завершения       |
| `result`      | `dict \| None`      | Результат             |
| `errors`      | `list[str] \| None` | Ошибки                |
| `is_active`   | `bool`              | Активна (soft-delete) |

### `TaskFilter`

| Поле               | Тип                    | Описание             |
| ------------------ | ---------------------- | -------------------- |
| `name`             | `str \| None`          | Фильтр по имени      |
| `description`      | `str \| None`          | Фильтр по описанию   |
| `priority`         | `TaskPriority \| None` | Фильтр по приоритету |
| `status`           | `TaskStatus \| None`   | Фильтр по статусу    |
| `created_at_from`  | `datetime \| None`     | Дата создания >=     |
| `created_at_to`    | `datetime \| None`     | Дата создания <=     |
| `started_at_from`  | `datetime \| None`     | Дата начала >=       |
| `started_at_to`    | `datetime \| None`     | Дата начала <=       |
| `finished_at_from` | `datetime \| None`     | Дата завершения >=   |
| `finished_at_to`   | `datetime \| None`     | Дата завершения <=   |

### `PaginatedResponse[T]`

| Поле          | Тип           | Описание                   |
| ------------- | ------------- | -------------------------- |
| `items`       | `list[T]`     | Элементы страницы          |
| `next_cursor` | `str \| None` | Курсор следующей страницы  |
| `has_next`    | `bool`        | Есть ли следующая страница |

---

## Статусы задач (`TaskStatus`)

| Значение                  | Enum          |
| ------------------------- | ------------- |
| `"Новая задача"`          | `NEW`         |
| `"Ожидает обработки"`     | `PENDING`     |
| `"В процессе выполнения"` | `IN_PROGRESS` |
| `"Завершена успешно"`     | `COMPLETED`   |
| `"Завершена с ошибкой"`   | `FAILED`      |
| `"Отменена"`              | `CANCELLED`   |

---

## Приоритеты задач (`TaskPriority`)

| Значение    | Enum     |
| ----------- | -------- |
| `"Низкий"`  | `LOW`    |
| `"Средний"` | `MEDIUM` |
| `"Высокий"` | `HIGH`   |

---

## Обработка ошибок

| Код                    | Описание                                                                     |
| ---------------------- | ---------------------------------------------------------------------------- |
| `404 Not Found`        | Задача не найдена                                                            |
| `409 Conflict`         | `IntegrityError` — конфликт данных (например, дублирование уникального поля) |
| `422 Validation Error` | Ошибка Pydantic-валидации (некорректные типы, пропущенные обязательные поля) |

---

## Примеры использования (curl)

### Создание задачи

```bash
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Расчёт отчёта",
    "description": "Сформировать месячный отчёт по продажам",
    "priority": "Высокий",
    "payload": {"report_type": "monthly", "period": "2024-01"}
  }'
```

### Получение списка задач с фильтрацией

```bash
# С фильтром по статусу и приоритету
curl -X GET "http://localhost:8000/api/v1/tasks?status=Новая+задача&priority=Высокий&limit=10"

# С фильтром по диапазону дат
curl -X GET "http://localhost:8000/api/v1/tasks?created_at_from=2024-01-01T00:00:00&created_at_to=2024-01-31T23:59:59"

# С курсорной пагинацией
curl -X GET "http://localhost:8000/api/v1/tasks?cursor=eyJpZCI6MTB9&limit=20"
```

### Получение задачи по ID

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/1"
```

### Отмена задачи

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/1"
```

### Получение статуса задачи

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/1/status"