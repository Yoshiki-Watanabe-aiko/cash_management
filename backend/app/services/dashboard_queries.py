import calendar
import datetime
import decimal
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AssetSnapshot, Budget, Category, Transaction
from app.services.transfer_detection import linked_transaction_ids

_HUNDRED = decimal.Decimal("100")


class NetWorthPoint(NamedTuple):
    snapshot_date: datetime.date
    net_worth: decimal.Decimal


class BudgetProgressItem(NamedTuple):
    category_id: int
    category_name: str
    budget_amount: decimal.Decimal
    spent_amount: decimal.Decimal
    progress_ratio: decimal.Decimal


class CashflowSummary(NamedTuple):
    income: decimal.Decimal
    expense: decimal.Decimal


class CategoryAmount(NamedTuple):
    category_id: int | None
    category_name: str
    amount: decimal.Decimal


def _months_ago(base: datetime.date, months: int) -> datetime.date:
    month_index = base.month - 1 - months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def _month_bounds(year_month: str) -> tuple[datetime.date, datetime.date]:
    year_str, month_str = year_month.split("-")
    year, month = int(year_str), int(month_str)
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last_day)


def net_worth_history(
    session: Session, months: int = 12, as_of: datetime.date | None = None
) -> list[NetWorthPoint]:
    """資産スナップショット日別の合計値(純資産)を直近Nヶ月分返す(5.5章)。"""
    as_of = as_of or datetime.date.today()
    since_date = _months_ago(as_of, months)

    stmt = (
        select(AssetSnapshot.snapshot_date, func.sum(AssetSnapshot.current_value).label("net_worth"))
        .where(AssetSnapshot.snapshot_date >= since_date, AssetSnapshot.snapshot_date <= as_of)
        .group_by(AssetSnapshot.snapshot_date)
        .order_by(AssetSnapshot.snapshot_date)
    )
    return [NetWorthPoint(row.snapshot_date, row.net_worth) for row in session.execute(stmt).all()]


def budget_progress(session: Session, year_month: str) -> list[BudgetProgressItem]:
    """当月の事業予算に対する消化率を按分後の事業分金額で算出する(5.4章、振替除外)。"""
    date_from, date_to = _month_bounds(year_month)
    excluded_ids = linked_transaction_ids(session)

    budgets = session.execute(
        select(Budget, Category.category_name)
        .join(Category, Category.id == Budget.category_id)
        .where(Budget.year_month == year_month, Budget.is_business.is_(True))
    ).all()
    if not budgets:
        return []

    category_ids = [budget.category_id for budget, _ in budgets]
    expense_rows = session.execute(
        select(Transaction.id, Transaction.category_id, Transaction.amount, Transaction.business_ratio).where(
            Transaction.category_id.in_(category_ids),
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
            Transaction.amount < 0,
        )
    ).all()

    spent_by_category: dict[int, decimal.Decimal] = {}
    for txn_id, category_id, amount, business_ratio in expense_rows:
        if txn_id in excluded_ids:
            continue
        spent_by_category[category_id] = spent_by_category.get(
            category_id, decimal.Decimal("0")
        ) + (-amount) * business_ratio / _HUNDRED

    results = []
    for budget, category_name in budgets:
        spent = spent_by_category.get(budget.category_id, decimal.Decimal("0"))
        progress_ratio = (spent / budget.budget_amount) if budget.budget_amount else decimal.Decimal("0")
        results.append(
            BudgetProgressItem(budget.category_id, category_name, budget.budget_amount, spent, progress_ratio)
        )
    return results


def personal_cashflow(session: Session, year_month: str) -> CashflowSummary:
    """個人口座のキャッシュフロー(収入 vs 支出)を按分後の個人分金額で算出する(振替除外)。"""
    date_from, date_to = _month_bounds(year_month)
    excluded_ids = linked_transaction_ids(session)

    rows = session.execute(
        select(Transaction.id, Transaction.amount, Transaction.business_ratio).where(
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
        )
    ).all()

    income = decimal.Decimal("0")
    expense = decimal.Decimal("0")
    for txn_id, amount, business_ratio in rows:
        if txn_id in excluded_ids:
            continue
        personal_amount = amount * (_HUNDRED - business_ratio) / _HUNDRED
        if personal_amount > 0:
            income += personal_amount
        else:
            expense += -personal_amount
    return CashflowSummary(income=income, expense=expense)


def category_breakdown(session: Session, year_month: str) -> list[CategoryAmount]:
    """カテゴリ別の支出金額を算出する(振替除外、事業按分はせず全額表示)。"""
    date_from, date_to = _month_bounds(year_month)
    excluded_ids = linked_transaction_ids(session)

    rows = session.execute(
        select(Transaction.id, Transaction.amount, Transaction.category_id, Category.category_name)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
            Transaction.amount < 0,
        )
    ).all()

    totals: dict[int | None, decimal.Decimal] = {}
    names: dict[int | None, str] = {}
    for txn_id, amount, category_id, category_name in rows:
        if txn_id in excluded_ids:
            continue
        totals[category_id] = totals.get(category_id, decimal.Decimal("0")) + (-amount)
        names[category_id] = category_name or "未分類"

    items = [
        CategoryAmount(category_id=cid, category_name=names[cid], amount=amount)
        for cid, amount in totals.items()
    ]
    items.sort(key=lambda item: item.amount, reverse=True)
    return items
