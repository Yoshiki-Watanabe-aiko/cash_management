import decimal

from pydantic import BaseModel, ConfigDict, Field


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    year_month: str
    is_business: bool
    budget_amount: decimal.Decimal


class BudgetCreate(BaseModel):
    category_id: int
    year_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    is_business: bool = True
    budget_amount: decimal.Decimal = Field(gt=0)


class BudgetUpdate(BaseModel):
    budget_amount: decimal.Decimal = Field(gt=0)
