import datetime
import decimal

from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    account_name: str
    account_type: str
    is_business: bool
    is_active: bool
    default_business_ratio: decimal.Decimal
    tracks_balance: bool
    balance_method: str | None
    opening_balance: decimal.Decimal | None
    opening_balance_date: datetime.date | None
    moneyforward_account_name: str | None
    card_last4: str | None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: str


class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_name: str
    institution_type: str
