import email.message
from typing import Protocol

from app.schemas.card_email import ParsedCardTransaction


class CardEmailParser(Protocol):
    """カード会社別メールパーサーのインターフェース。

    実メールサンプル入手後、会社ごとの実装を追加しregistry.register_parser()へ登録する(ADR 0010)。
    """

    def parse(self, message: email.message.Message) -> ParsedCardTransaction | None: ...
