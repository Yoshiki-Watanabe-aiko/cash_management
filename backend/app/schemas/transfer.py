import datetime
import decimal

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


class LinkedTransferTransaction(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_date: datetime.date
    amount: decimal.Decimal
    description: str
    account_id: int | None


class LinkedTransferRead(BaseModel):
    id: int
    match_confidence: str
    linked_at: datetime.datetime
    from_transaction: LinkedTransferTransaction
    to_transaction: LinkedTransferTransaction
