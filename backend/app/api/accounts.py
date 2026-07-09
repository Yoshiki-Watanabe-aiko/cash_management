from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.reference import AccountRead
from app.services import account_management
from app.services.account_management import AccountValidationError

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=201)
def post_account(payload: AccountCreate, db: Session = Depends(get_db)) -> AccountRead:
    fields = payload.model_dump()
    institution_id = fields.pop("institution_id")
    try:
        account = account_management.create_account(db, institution_id=institution_id, **fields)
    except AccountValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=AccountRead)
def patch_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)) -> AccountRead:
    updates = payload.model_dump(exclude_unset=True)
    try:
        account = account_management.update_account(db, account_id, updates)
    except AccountValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if account is None:
        raise HTTPException(status_code=404, detail="口座が見つかりません")
    return AccountRead.model_validate(account)
