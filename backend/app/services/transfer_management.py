import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.core.business_days import business_days_between
from app.models import Transaction, Transfer
from app.services.transfer_detection import find_transfer_candidates, linked_transaction_ids

_MAX_BUSINESS_DAY_GAP = 3


class TransferLinkError(ValueError):
    """手動振替紐づけのバリデーションエラー。"""


def list_unlinked_candidates(session: Session, as_of: datetime.date) -> list[Transaction]:
    """直近7日以内・未リンクの取引を手動紐づけ候補として返す。"""
    return find_transfer_candidates(session, as_of)


def list_linked_transfers(session: Session) -> list[tuple[Transfer, Transaction, Transaction]]:
    """紐づけ済みの振替を、出金・入金それぞれの取引情報付きで新しい順に返す。"""
    from_txn = aliased(Transaction)
    to_txn = aliased(Transaction)
    stmt = (
        select(Transfer, from_txn, to_txn)
        .join(from_txn, Transfer.from_transaction_id == from_txn.id)
        .join(to_txn, Transfer.to_transaction_id == to_txn.id)
        .order_by(Transfer.linked_at.desc())
    )
    return session.execute(stmt).all()


def create_manual_transfer_link(session: Session, from_transaction_id: int, to_transaction_id: int) -> Transfer:
    """条件1(金額完全一致)・条件2(営業日0〜3日以内)のみ検証し、条件3(摘要一致)は手動判断に委ねて紐づける(5.2章)。"""
    if from_transaction_id == to_transaction_id:
        raise TransferLinkError("同一取引は紐づけできません")

    from_txn = session.get(Transaction, from_transaction_id)
    to_txn = session.get(Transaction, to_transaction_id)
    if from_txn is None or to_txn is None:
        raise TransferLinkError("指定された取引が見つかりません")

    already_linked = linked_transaction_ids(session)
    if from_transaction_id in already_linked or to_transaction_id in already_linked:
        raise TransferLinkError("既に振替リンク済みの取引です")

    if abs(from_txn.amount) != abs(to_txn.amount):
        raise TransferLinkError("金額が一致しません")
    if from_txn.amount >= 0 or to_txn.amount <= 0:
        raise TransferLinkError("出金取引と入金取引の組み合わせではありません")
    if business_days_between(from_txn.transaction_date, to_txn.transaction_date) > _MAX_BUSINESS_DAY_GAP:
        raise TransferLinkError("営業日ベースで4日以上離れています")

    transfer = Transfer(
        from_transaction_id=from_transaction_id,
        to_transaction_id=to_transaction_id,
        match_confidence="manual",
    )
    session.add(transfer)
    session.flush()
    return transfer


def delete_transfer_link(session: Session, transfer_id: int) -> bool:
    """振替リンクを解除する(紐づけていた取引自体は削除しない)。"""
    transfer = session.get(Transfer, transfer_id)
    if transfer is None:
        return False
    session.delete(transfer)
    session.flush()
    return True
