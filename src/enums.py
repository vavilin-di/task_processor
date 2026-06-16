from enum import StrEnum


class TaskStatus(StrEnum):
    NEW = "Новая задача"
    PENDING = "Ожидает обработки"
    IN_PROGRESS = "В процессе выполнения"
    COMPLETED = "Завершена успешно"
    FAILED = "Завершена с ошибкой"
    CANCELLED = "Отменена"


class TaskPriority(StrEnum):
    LOW = "Низкий"
    MEDIUM = "Средний"
    HIGH = "Высокий"
