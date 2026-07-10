import datetime
import decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    transaction_date: datetime.date
    amount: decimal.Decimal
    description: str
    category_id: int | None
    business_ratio: decimal.Decimal
    source_type: str
    is_transferred: bool = False


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    page_size: int


class TransactionUpdate(BaseModel):
    category_id: int | None = None
    business_ratio: decimal.Decimal | None = Field(default=None, ge=0, le=100)


class TransactionCreate(BaseModel):
    account_id: int | None = None
    transaction_date: datetime.date
    amount: decimal.Decimal
    description: str = Field(min_length=1, max_length=500)
    category_id: int | None = None
    business_ratio: decimal.Decimal = Field(default=decimal.Decimal("100.00"), ge=0, le=100)


class RecategorizeResult(BaseModel):
    updated_count: int
