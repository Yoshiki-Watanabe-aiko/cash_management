import decimal

from app.services.mf_assets_csv import parse_assets_csv

_HEADER = "日付,保有金融機関,銘柄,評価額（円）,取得金額（円）\n"


def test_parses_basic_row(tmp_path):
    csv_text = _HEADER + "2026/07/01,楽天証券,eMAXIS Slim米国株式,500000,450000\n"
    path = tmp_path / "assets.csv"
    path.write_text(csv_text, encoding="utf-8-sig")

    rows = parse_assets_csv(path)

    assert len(rows) == 1
    row = rows[0]
    assert row.institution_label == "楽天証券"
    assert row.ticker_or_name == "eMAXIS Slim米国株式"
    assert row.current_value == decimal.Decimal("500000")
    assert row.book_value == decimal.Decimal("450000")


def test_book_value_is_optional(tmp_path):
    csv_text = _HEADER + "2026/07/01,三井住友銀行,ローン,-2000000,\n"
    path = tmp_path / "assets.csv"
    path.write_text(csv_text, encoding="utf-8-sig")

    rows = parse_assets_csv(path)

    assert rows[0].book_value is None
    assert rows[0].current_value == decimal.Decimal("-2000000")
