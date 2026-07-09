import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Budget, Category


class BudgetValidationError(ValueError):
    """予算作成時のバリデーションエラー(カテゴリ不在・重複)。"""


def list_budgets(
    session: Session, *, year_month: str | None = None, is_business: bool | None = None
) -> list[Budget]:
    """予算一覧を年月降順・カテゴリID昇順で返す。"""
    filters = []
    if year_month is not None:
        filters.append(Budget.year_month == year_month)
    if is_business is not None:
        filters.append(Budget.is_business == is_business)
    stmt = select(Budget).where(*filters).order_by(Budget.year_month.desc(), Budget.category_id)
    return session.execute(stmt).scalars().all()


def create_budget(
    session: Session,
    *,
    category_id: int,
    year_month: str,
    is_business: bool,
    budget_amount: decimal.Decimal,
) -> Budget:
    """カテゴリ×年月×個人/事業区分ごとに予算を新規作成する(重複は不可)。"""
    if session.get(Category, category_id) is None:
        raise BudgetValidationError("指定されたカテゴリが見つかりません")

    duplicate = session.execute(
        select(Budget.id).where(
            Budget.category_id == category_id,
            Budget.year_month == year_month,
            Budget.is_business == is_business,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise BudgetValidationError("同一カテゴリ・年月・区分の予算は既に登録されています")

    budget = Budget(
        category_id=category_id,
        year_month=year_month,
        is_business=is_business,
        budget_amount=budget_amount,
    )
    session.add(budget)
    session.flush()
    return budget


def update_budget(session: Session, budget_id: int, budget_amount: decimal.Decimal) -> Budget | None:
    """予算金額のみを更新する。"""
    budget = session.get(Budget, budget_id)
    if budget is None:
        return None
    budget.budget_amount = budget_amount
    session.flush()
    return budget


def delete_budget(session: Session, budget_id: int) -> bool:
    """予算を削除する。"""
    budget = session.get(Budget, budget_id)
    if budget is None:
        return False
    session.delete(budget)
    session.flush()
    return True
