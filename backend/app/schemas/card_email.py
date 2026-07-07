import dataclasses
import datetime
import decimal


@dataclasses.dataclass(frozen=True)
class ParsedCardTransaction:
    """カード利用速報メールから抽出した1件の利用実績(amountは支出のため必ずマイナス値)。"""

    transaction_date: datetime.date
    amount: decimal.Decimal
    description: str
    message_id: str
    card_last4: str | None = None
