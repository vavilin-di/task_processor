from typing import Any

from pydantic import BaseModel
from pydantic.config import ConfigDict


class OutboxMessageCreate(BaseModel):
    routing_key: str
    aggregate_id: int
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class OutboxMessage(BaseModel):
    id: int
    routing_key: str
    payload: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
