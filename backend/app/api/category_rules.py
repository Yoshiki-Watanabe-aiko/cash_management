from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category_rule import CategoryRuleCreate, CategoryRuleRead, CategoryRuleUpdate
from app.services import category_rule_management
from app.services.category_rule_management import CategoryRuleValidationError

router = APIRouter(prefix="/api/category-rules", tags=["category-rules"])


@router.get("", response_model=list[CategoryRuleRead])
def get_category_rules(db: Session = Depends(get_db)) -> list[CategoryRuleRead]:
    rules = category_rule_management.list_category_rules(db)
    return [CategoryRuleRead.model_validate(rule) for rule in rules]


@router.post("", response_model=CategoryRuleRead, status_code=201)
def post_category_rule(payload: CategoryRuleCreate, db: Session = Depends(get_db)) -> CategoryRuleRead:
    try:
        rule = category_rule_management.create_category_rule(
            db,
            keyword_pattern=payload.keyword_pattern,
            category_id=payload.category_id,
            priority=payload.priority,
        )
    except CategoryRuleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CategoryRuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=CategoryRuleRead)
def patch_category_rule(
    rule_id: int, payload: CategoryRuleUpdate, db: Session = Depends(get_db)
) -> CategoryRuleRead:
    updates = payload.model_dump(exclude_unset=True)
    try:
        rule = category_rule_management.update_category_rule(db, rule_id, updates)
    except CategoryRuleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if rule is None:
        raise HTTPException(status_code=404, detail="カテゴリルールが見つかりません")
    return CategoryRuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_category_rule(rule_id: int, db: Session = Depends(get_db)) -> None:
    deleted = category_rule_management.delete_category_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="カテゴリルールが見つかりません")
