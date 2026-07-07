import datetime
import decimal
import hashlib


def compute_source_hash(
    account_id: int | None,
    transaction_date: datetime.date,
    amount: decimal.Decimal,
    description: str,
    source_unique_id: str,
) -> str:
    """t_transactions.source_hash算出(ADR 0003: account_id+日付+金額+摘要+ソース側一意識別子)。"""
    parts = [
        str(account_id) if account_id is not None else "",
        transaction_date.isoformat(),
        format(amount.normalize(), "f"),
        description,
        source_unique_id,
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
