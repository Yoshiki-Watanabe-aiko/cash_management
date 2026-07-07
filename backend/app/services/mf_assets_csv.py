"""マネーフォワードME 資産評価CSVのパーサー。

注意: 実際のCSVサンプルが未入手のため、列名は一般的に知られている表記のエイリアスを
複数登録して吸収する設計にしている。実サンプル入手後は _COLUMN_ALIASES のみ調整すればよい。
"""

import csv
import datetime
import decimal
import io
from pathlib import Path

from app.schemas.moneyforward import MfAssetRow

_CANDIDATE_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "cp932")

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("日付", "評価日"),
    "institution_label": ("保有金融機関", "金融機関", "口座"),
    "ticker_or_name": ("銘柄", "名称", "銘柄名"),
    "current_value": ("評価額（円）", "評価額(円)", "評価額"),
    "book_value": ("取得金額（円）", "取得金額(円)", "取得金額", "取得価額"),
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


def _find_column(row: dict[str, str], field: str) -> str | None:
    for name in _COLUMN_ALIASES[field]:
        if name in row:
            return name
    return None


def _get_required(row: dict[str, str], field: str) -> str:
    column = _find_column(row, field)
    if column is None:
        raise KeyError(f"CSVに必須列が見つかりません: {_COLUMN_ALIASES[field]}")
    return (row[column] or "").strip()


def _get_optional_decimal(row: dict[str, str], field: str) -> decimal.Decimal | None:
    column = _find_column(row, field)
    if column is None:
        return None
    value = (row[column] or "").strip()
    if not value:
        return None
    return decimal.Decimal(value.replace(",", ""))


def parse_assets_csv(path: Path) -> list[MfAssetRow]:
    """マネーフォワードME 資産評価CSVをパースする。"""
    text = _read_text(path)
    reader = csv.DictReader(io.StringIO(text))
    rows: list[MfAssetRow] = []

    for raw_row in reader:
        snapshot_date = datetime.datetime.strptime(_get_required(raw_row, "date"), "%Y/%m/%d").date()
        current_value = decimal.Decimal(_get_required(raw_row, "current_value").replace(",", ""))

        rows.append(
            MfAssetRow(
                snapshot_date=snapshot_date,
                institution_label=_get_required(raw_row, "institution_label"),
                ticker_or_name=_get_required(raw_row, "ticker_or_name"),
                current_value=current_value,
                book_value=_get_optional_decimal(raw_row, "book_value"),
            )
        )

    return rows
