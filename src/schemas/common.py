from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    items: list[T]
    next_cursor: str | None
    has_next: bool
