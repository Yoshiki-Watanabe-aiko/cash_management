import datetime

from pydantic import BaseModel, ConfigDict


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_transaction_id: int
    to_transaction_id: int
    match_confidence: str
    linked_at: datetime.datetime


class TransferCreate(BaseModel):
    from_transaction_id: int
    to_transaction_id: int
