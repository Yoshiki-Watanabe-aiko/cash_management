import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import BudgetProgressItem, CashflowSummary, CategoryAmount, NetWorthPoint
from app.services import dashboard_queries

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _current_year_month() -> str:
    today = datetime.date.today()
    return f"{today.year:04d}-{today.month:02d}"


@router.get("/net-worth-history", response_model=list[NetWorthPoint])
def get_net_worth_history(
    months: int = Query(default=12, ge=1, le=60), db: Session = Depends(get_db)
) -> list:
    return dashboard_queries.net_worth_history(db, months=months)


@router.get("/budget-progress", response_model=list[BudgetProgressItem])
def get_budget_progress(year_month: str | None = None, db: Session = Depends(get_db)) -> list:
    return dashboard_queries.budget_progress(db, year_month=year_month or _current_year_month())


@router.get("/personal-cashflow", response_model=CashflowSummary)
def get_personal_cashflow(year_month: str | None = None, db: Session = Depends(get_db)):
    return dashboard_queries.personal_cashflow(db, year_month=year_month or _current_year_month())


@router.get("/category-breakdown", response_model=list[CategoryAmount])
def get_category_breakdown(year_month: str | None = None, db: Session = Depends(get_db)) -> list:
    return dashboard_queries.category_breakdown(db, year_month=year_month or _current_year_month())
