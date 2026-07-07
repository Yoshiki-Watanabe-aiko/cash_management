import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import (
    RecategorizeResult,
    TransactionListResponse,
    TransactionRead,
    TransactionUpdate,
)
from app.services import transaction_queries

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _to_read_model(txn, is_transferred: bool) -> TransactionRead:
    return TransactionRead.model_validate(txn).model_copy(update={"is_transferred": is_transferred})


@router.get("", response_model=TransactionListResponse)
def get_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    uncategorized_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    rows, total = transaction_queries.list_transactions(
        db,
        account_id=account_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        uncategorized_only=uncategorized_only,
        page=page,
        page_size=page_size,
    )
    items = [_to_read_model(txn, is_transferred) for txn, is_transferred in rows]
    return TransactionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def patch_transaction(
    transaction_id: int, update: TransactionUpdate, db: Session = Depends(get_db)
) -> TransactionRead:
    updates = update.model_dump(exclude_unset=True)
    try:
        txn = transaction_queries.update_transaction(db, transaction_id, updates)
    except transaction_queries.TransactionUpdateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if txn is None:
        raise HTTPException(status_code=404, detail="取引が見つかりません")
    is_transferred = transaction_queries.is_transaction_transferred(db, transaction_id)
    return _to_read_model(txn, is_transferred)


@router.post("/recategorize", response_model=RecategorizeResult)
def post_recategorize(db: Session = Depends(get_db)) -> RecategorizeResult:
    updated_count = transaction_queries.recategorize_uncategorized(db)
    return RecategorizeResult(updated_count=updated_count)
