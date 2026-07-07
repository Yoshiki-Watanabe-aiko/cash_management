import decimal

from app.services.mf_transactions_csv import parse_transactions_csv

_HEADER = "計算対象,日付,内容,金額（円）,保有金融機関,大項目,中項目,メモ,振替,ID\n"


def test_parses_basic_row(tmp_path):
    csv_text = _HEADER + '1,2026/07/01,スーパーA,"-1,500",楽天銀行,食費,食料品,,0,mf-001\n'
    path = tmp_path / "transactions.csv"
    path.write_text(csv_text, encoding="utf-8-sig")

    rows = parse_transactions_csv(path)

    assert len(rows) == 1
    row = rows[0]
    assert row.description == "スーパーA"
    assert row.amount == decimal.Decimal("-1500")
    assert row.institution_label == "楽天銀行"
    assert row.source_unique_id == "mf-001"
    assert row.mf_is_transfer is False


def test_skips_rows_excluded_from_calculation(tmp_path):
    csv_text = (
        _HEADER
        + "1,2026/07/01,対象内,-1000,楽天銀行,食費,食料品,,0,mf-001\n"
        + "0,2026/07/02,対象外,-2000,楽天銀行,食費,食料品,,0,mf-002\n"
    )
    path = tmp_path / "transactions.csv"
    path.write_text(csv_text, encoding="utf-8-sig")

    rows = parse_transactions_csv(path)

    assert len(rows) == 1
    assert rows[0].source_unique_id == "mf-001"


def test_mf_transfer_flag_is_captured(tmp_path):
    csv_text = _HEADER + "1,2026/07/01,振替入金,10000,楽天銀行,,,,1,mf-003\n"
    path = tmp_path / "transactions.csv"
    path.write_text(csv_text, encoding="utf-8-sig")

    rows = parse_transactions_csv(path)

    assert rows[0].mf_is_transfer is True
    assert rows[0].amount == decimal.Decimal("10000")


def test_parses_cp932_encoded_file(tmp_path):
    csv_text = _HEADER + "1,2026/07/01,コンビニ,-500,楽天カード,,,,0,mf-004\n"
    path = tmp_path / "transactions_sjis.csv"
    path.write_bytes(csv_text.encode("cp932"))

    rows = parse_transactions_csv(path)

    assert rows[0].description == "コンビニ"
