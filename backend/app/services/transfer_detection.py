import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.business_days import business_days_between
from app.core.config import settings
from app.models import Account, Transaction, Transfer

_WHITESPACE_CHARS = str.maketrans("", "", " 　")
_LOOKBACK_DAYS = 7
_MAX_BUSINESS_DAY_GAP = 3


def _normalize(text: str) -> str:
    return text.translate(_WHITESPACE_CHARS)


def _linked_transaction_ids(session: Session) -> set[int]:
    linked_from = session.execute(select(Transfer.from_transaction_id)).scalars().all()
    linked_to = session.execute(select(Transfer.to_transaction_id)).scalars().all()
    return set(linked_from) | set(linked_to)


def find_transfer_candidates(session: Session, as_of: datetime.date) -> list[Transaction]:
    """直近7日以内・未リンクの取引を振替検知の候補として取得する(ADR 0005)。"""
    since_date = as_of - datetime.timedelta(days=_LOOKBACK_DAYS)
    linked_ids = _linked_transaction_ids(session)

    stmt = select(Transaction).where(Transaction.transaction_date >= since_date)
    candidates = session.execute(stmt).scalars().all()
    return [c for c in candidates if c.id not in linked_ids]


def _name_tokens(session: Session) -> list[str]:
    account_names = session.execute(select(Account.account_name)).scalars().all()
    return [_normalize(name) for name in (*settings.account_holder_names_list, *account_names) if name]


def _description_matches_name(description: str, name_tokens: list[str]) -> bool:
    normalized_description = _normalize(description)
    return any(token in normalized_description for token in name_tokens)


def _is_transfer_pair(a: Transaction, b: Transaction, name_tokens: list[str]) -> bool:
    if a.account_id == b.account_id:
        return False
    if abs(a.amount) != abs(b.amount):
        return False
    if (a.amount < 0) == (b.amount < 0):
        return False
    if business_days_between(a.transaction_date, b.transaction_date) > _MAX_BUSINESS_DAY_GAP:
        return False
    return _description_matches_name(a.description, name_tokens) or _description_matches_name(
        b.description, name_tokens
    )


def detect_and_link_transfers(session: Session, as_of: datetime.date) -> int:
    """振替候補ペアを検知しt_transfersへリンクする。リンク件数を返す。"""
    candidates = find_transfer_candidates(session, as_of)
    name_tokens = _name_tokens(session)

    used_ids: set[int] = set()
    linked_count = 0

    for i, txn_a in enumerate(candidates):
        if txn_a.id in used_ids:
            continue
        for txn_b in candidates[i + 1 :]:
            if txn_b.id in used_ids:
                continue
            if not _is_transfer_pair(txn_a, txn_b, name_tokens):
                continue

            from_txn, to_txn = (txn_a, txn_b) if txn_a.amount < 0 else (txn_b, txn_a)
            session.add(
                Transfer(
                    from_transaction_id=from_txn.id,
                    to_transaction_id=to_txn.id,
                    match_confidence="auto",
                )
            )
            used_ids.add(txn_a.id)
            used_ids.add(txn_b.id)
            linked_count += 1
            break

    return linked_count
