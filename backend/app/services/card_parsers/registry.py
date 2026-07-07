from app.services.card_parsers.base import CardEmailParser

_PARSERS: dict[str, CardEmailParser] = {}
"""institution_name(m_institutions.institution_name) → パーサー実装のレジストリ。

実メールサンプル入手後、カード会社ごとにregister_parser()で追加する(要件定義書4.1/9章、ADR 0010)。
現時点ではどの会社も登録されておらず、find_parser()は常にNoneを返す。
"""


def register_parser(institution_name: str, parser: CardEmailParser) -> None:
    _PARSERS[institution_name] = parser


def find_parser(institution_name: str) -> CardEmailParser | None:
    return _PARSERS.get(institution_name)
