from pydantic import BaseModel


class OutboxMessageCreate(BaseModel):
    routing_key: str
    aggregate_id: int
    payload: dict


class OutboxMessage(BaseModel):
    id: int
    routing_key: str
    payload: dict
