import csv
import datetime
import decimal
import io
from pathlib import Path

from app.schemas.moneyforward import MfTransactionRow

_CANDIDATE_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "cp932")

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "calc_target": ("計算対象",),
    "date": ("日付",),
    "description": ("内容",),
    "amount": ("金額（円）", "金額(円)"),
    "institution_label": ("保有金融機関",),
    "major_category": ("大項目",),
    "minor_category": ("中項目",),
    "memo": ("メモ",),
    "is_transfer": ("振替",),
    "source_unique_id": ("ID",),
}


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in _CANDIDATE_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        _CANDIDATE_ENCODINGS[-1], raw, 0, 1, f"{path}をサポート対象エンコーディングで復号できませんでした"
    )


def _get(row: dict[str, str], field: str) -> str:
    for name in _COLUMN_ALIASES[field]:
        if name in row:
            return (row[name] or "").strip()
    raise KeyError(f"CSVに必須列が見つかりません: {_COLUMN_ALIASES[field]}")


def parse_transactions_csv(path: Path) -> list[MfTransactionRow]:
    """マネーフォワードME「収入・支出詳細」CSVをパースし、計算対象外の行を除外して返す。"""
    text = _read_text(path)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[MfTransactionRow] = []

    for raw_row in reader:
        if _get(raw_row, "calc_target") == "0":
            continue

        transaction_date = datetime.datetime.strptime(_get(raw_row, "date"), "%Y/%m/%d").date()
        amount = decimal.Decimal(_get(raw_row, "amount").replace(",", ""))

        rows.append(
            MfTransactionRow(
                transaction_date=transaction_date,
                description=_get(raw_row, "description"),
                amount=amount,
                institution_label=_get(raw_row, "institution_label"),
                major_category=_get(raw_row, "major_category"),
                minor_category=_get(raw_row, "minor_category"),
                memo=_get(raw_row, "memo"),
                mf_is_transfer=_get(raw_row, "is_transfer") == "1",
                source_unique_id=_get(raw_row, "source_unique_id"),
            )
        )

    return rows
