from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DLQMessageCreate(BaseModel):
    original_routing_key: str
    original_payload: dict
    error_type: str
    error_message: str
    retry_count: int
    x_death: list[dict[str, Any]] | None


class DLQMessage(BaseModel):
    id: int
    original_routing_key: str
    original_payload: dict
    error_type: str
    error_message: str
    retry_count: int
    x_death: list[dict[str, Any]] | None
    created_at: datetime
