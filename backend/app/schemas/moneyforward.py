import datetime
import decimal
from dataclasses import dataclass


@dataclass(frozen=True)
class MfTransactionRow:
    """マネーフォワードME「収入・支出詳細」CSVの1行を正規化した中間表現。"""

    transaction_date: datetime.date
    description: str
    amount: decimal.Decimal
    institution_label: str
    major_category: str
    minor_category: str
    memo: str
    mf_is_transfer: bool
    source_unique_id: str


@dataclass(frozen=True)
class MfAssetRow:
    """マネーフォワードME 資産評価CSVの1行を正規化した中間表現。"""

    snapshot_date: datetime.date
    institution_label: str
    ticker_or_name: str
    current_value: decimal.Decimal
    book_value: decimal.Decimal | None
