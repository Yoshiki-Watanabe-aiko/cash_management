from pydantic import BaseModel, ConfigDict


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str
    account_type: str
    is_business: bool
    is_active: bool
    tracks_balance: bool


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: str
