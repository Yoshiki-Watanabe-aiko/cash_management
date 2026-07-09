import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import TransactionRead
from app.schemas.transfer import LinkedTransferRead, LinkedTransferTransaction, TransferCreate, TransferRead
from app.services import transfer_management
from app.services.transfer_management import TransferLinkError

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("", response_model=list[LinkedTransferRead])
def get_linked_transfers(db: Session = Depends(get_db)) -> list[LinkedTransferRead]:
    rows = transfer_management.list_linked_transfers(db)
    return [
        LinkedTransferRead(
            id=transfer.id,
            match_confidence=transfer.match_confidence,
            linked_at=transfer.linked_at,
            from_transaction=LinkedTransferTransaction.model_validate(from_txn),
            to_transaction=LinkedTransferTransaction.model_validate(to_txn),
        )
        for transfer, from_txn, to_txn in rows
    ]


@router.get("/unlinked-candidates", response_model=list[TransactionRead])
def get_unlinked_candidates(
    as_of: datetime.date | None = None, db: Session = Depends(get_db)
) -> list[TransactionRead]:
    candidates = transfer_management.list_unlinked_candidates(db, as_of or datetime.date.today())
    return [TransactionRead.model_validate(txn) for txn in candidates]


@router.post("", response_model=TransferRead, status_code=201)
def post_transfer(payload: TransferCreate, db: Session = Depends(get_db)):
    try:
        return transfer_management.create_manual_transfer_link(
            db, payload.from_transaction_id, payload.to_transaction_id
        )
    except TransferLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{transfer_id}", status_code=204)
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)) -> None:
    deleted = transfer_management.delete_transfer_link(db, transfer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="振替リンクが見つかりません")
