import decimal

import pytest
from sqlalchemy import select

from app.models import Budget, Category
from app.services import budget_management
from app.services.budget_management import BudgetValidationError


def _category_id(session, name: str) -> int:
    return session.execute(select(Category.id).where(Category.category_name == name)).scalar_one()


def test_create_budget_persists_new_row(db_session):
    category_id = _category_id(db_session, "食費")

    budget = budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-07",
        is_business=False,
        budget_amount=decimal.Decimal("30000"),
    )

    assert budget.id is not None
    assert db_session.get(Budget, budget.id).budget_amount == decimal.Decimal("30000")


def test_create_budget_rejects_unknown_category(db_session):
    with pytest.raises(BudgetValidationError):
        budget_management.create_budget(
            db_session,
            category_id=999999999,
            year_month="2026-07",
            is_business=False,
            budget_amount=decimal.Decimal("30000"),
        )


def test_create_budget_rejects_duplicate_category_month_and_business_flag(db_session):
    category_id = _category_id(db_session, "交通費")
    budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-07",
        is_business=True,
        budget_amount=decimal.Decimal("10000"),
    )

    with pytest.raises(BudgetValidationError):
        budget_management.create_budget(
            db_session,
            category_id=category_id,
            year_month="2026-07",
            is_business=True,
            budget_amount=decimal.Decimal("20000"),
        )


def test_list_budgets_filters_by_year_month_and_is_business(db_session):
    category_id = _category_id(db_session, "通信費")
    budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-08",
        is_business=True,
        budget_amount=decimal.Decimal("5000"),
    )
    budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-08",
        is_business=False,
        budget_amount=decimal.Decimal("3000"),
    )

    business_only = budget_management.list_budgets(db_session, year_month="2026-08", is_business=True)

    assert len(business_only) == 1
    assert business_only[0].is_business is True


def test_update_budget_changes_amount(db_session):
    category_id = _category_id(db_session, "水道光熱費")
    budget = budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-09",
        is_business=True,
        budget_amount=decimal.Decimal("8000"),
    )

    updated = budget_management.update_budget(db_session, budget.id, decimal.Decimal("9000"))

    assert updated.budget_amount == decimal.Decimal("9000")


def test_update_budget_returns_none_when_not_found(db_session):
    result = budget_management.update_budget(db_session, 999999999, decimal.Decimal("1000"))
    assert result is None


def test_delete_budget_removes_row(db_session):
    category_id = _category_id(db_session, "医療費")
    budget = budget_management.create_budget(
        db_session,
        category_id=category_id,
        year_month="2026-10",
        is_business=False,
        budget_amount=decimal.Decimal("4000"),
    )

    deleted = budget_management.delete_budget(db_session, budget.id)

    assert deleted is True
    assert db_session.get(Budget, budget.id) is None


def test_delete_budget_returns_false_when_not_found(db_session):
    assert budget_management.delete_budget(db_session, 999999999) is False
