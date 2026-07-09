import datetime
import decimal

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    institution_id: int
    account_name: str = Field(min_length=1)
    account_type: str
    is_business: bool = False
    is_active: bool = True
    default_business_ratio: decimal.Decimal = Field(default=decimal.Decimal("100.00"), ge=0, le=100)
    tracks_balance: bool = False
    balance_method: str | None = None
    opening_balance: decimal.Decimal | None = None
    opening_balance_date: datetime.date | None = None
    moneyforward_account_name: str | None = None
    card_last4: str | None = Field(default=None, pattern=r"^\d{4}$")


class AccountUpdate(BaseModel):
    institution_id: int | None = None
    account_name: str | None = Field(default=None, min_length=1)
    account_type: str | None = None
    is_business: bool | None = None
    is_active: bool | None = None
    default_business_ratio: decimal.Decimal | None = Field(default=None, ge=0, le=100)
    tracks_balance: bool | None = None
    balance_method: str | None = None
    opening_balance: decimal.Decimal | None = None
    opening_balance_date: datetime.date | None = None
    moneyforward_account_name: str | None = None
    card_last4: str | None = Field(default=None, pattern=r"^\d{4}$")
