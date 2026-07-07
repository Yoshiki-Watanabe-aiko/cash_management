from app.services.card_parsers.registry import _PARSERS, find_parser, register_parser


class _StubParser:
    def parse(self, message):
        return None


def test_find_parser_returns_none_when_unregistered():
    assert find_parser("存在しないカード会社") is None


def test_register_and_find_parser_roundtrip():
    register_parser("テストカード会社", _StubParser())
    try:
        parser = find_parser("テストカード会社")
        assert parser is not None
        assert isinstance(parser, _StubParser)
    finally:
        _PARSERS.pop("テストカード会社", None)
