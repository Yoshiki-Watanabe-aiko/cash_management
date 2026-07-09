from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate
from app.services import budget_management
from app.services.budget_management import BudgetValidationError

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetRead])
def get_budgets(
    year_month: str | None = None, is_business: bool | None = None, db: Session = Depends(get_db)
) -> list[BudgetRead]:
    budgets = budget_management.list_budgets(db, year_month=year_month, is_business=is_business)
    return [BudgetRead.model_validate(budget) for budget in budgets]


@router.post("", response_model=BudgetRead, status_code=201)
def post_budget(payload: BudgetCreate, db: Session = Depends(get_db)) -> BudgetRead:
    try:
        budget = budget_management.create_budget(
            db,
            category_id=payload.category_id,
            year_month=payload.year_month,
            is_business=payload.is_business,
            budget_amount=payload.budget_amount,
        )
    except BudgetValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BudgetRead.model_validate(budget)


@router.patch("/{budget_id}", response_model=BudgetRead)
def patch_budget(budget_id: int, payload: BudgetUpdate, db: Session = Depends(get_db)) -> BudgetRead:
    budget = budget_management.update_budget(db, budget_id, payload.budget_amount)
    if budget is None:
        raise HTTPException(status_code=404, detail="予算が見つかりません")
    return BudgetRead.model_validate(budget)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db)) -> None:
    deleted = budget_management.delete_budget(db, budget_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="予算が見つかりません")
