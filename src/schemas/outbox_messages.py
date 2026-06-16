from pydantic import BaseModel


class OutboxMessageCreate(BaseModel):
    routing_key: str
    aggregate_id: int
    payload: dict
    is_published: bool = False
    is_active: bool = True


class OutboxMessage(OutboxMessageCreate):
    id: int
