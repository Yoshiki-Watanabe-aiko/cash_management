import datetime
import decimal

from pydantic import BaseModel, ConfigDict


class NetWorthPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: datetime.date
    net_worth: decimal.Decimal


class BudgetProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    category_name: str
    budget_amount: decimal.Decimal
    spent_amount: decimal.Decimal
    progress_ratio: decimal.Decimal


class CashflowSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    income: decimal.Decimal
    expense: decimal.Decimal


class CategoryAmount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int | None
    category_name: str
    amount: decimal.Decimal
