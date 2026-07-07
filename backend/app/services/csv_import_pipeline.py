import datetime
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Account, Transaction
from app.services.account_resolver import resolve_account
from app.services.balance_snapshot import (
    write_cumulative_snapshot,
    write_moneyforward_loan_snapshot,
    write_moneyforward_securities_snapshot,
)
from app.services.categorization import categorize
from app.services.dedup import compute_source_hash
from app.services.mf_assets_csv import parse_assets_csv
from app.services.mf_transactions_csv import parse_transactions_csv
from app.services.transfer_detection import detect_and_link_transfers

_DEFAULT_BUSINESS_RATIO = 100
_TRANSACTIONS_SOURCE_TYPE = "moneyforward_csv"


@dataclass
class ImportSummary:
    files_processed: int = 0
    new_transaction_count: int = 0
    duplicate_skipped_count: int = 0
    unresolved_institution_labels: list[str] = field(default_factory=list)
    asset_snapshot_count: int = 0
    transfer_detected_count: int = 0


def _list_csv_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.csv") if p.is_file())


def _move_to_processed(path: Path, as_of: datetime.date) -> None:
    processed_dir = path.parent / "processed" / as_of.isoformat()
    processed_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(processed_dir / path.name))


def _import_transactions_file(session: Session, path: Path, summary: ImportSummary) -> None:
    rows = parse_transactions_csv(path)

    for row in rows:
        account = resolve_account(session, row.institution_label)
        if account is None:
            summary.unresolved_institution_labels.append(row.institution_label)

        account_id = account.id if account else None
        business_ratio = account.default_business_ratio if account else _DEFAULT_BUSINESS_RATIO
        category_id = categorize(session, row.description)
        source_hash = compute_source_hash(
            account_id, row.transaction_date, row.amount, row.description, row.source_unique_id
        )
        raw_data = {
            "institution_label": row.institution_label,
            "major_category": row.major_category,
            "minor_category": row.minor_category,
            "memo": row.memo,
            "mf_is_transfer": row.mf_is_transfer,
            "source_unique_id": row.source_unique_id,
        }

        stmt = (
            pg_insert(Transaction)
            .values(
                account_id=account_id,
                transaction_date=row.transaction_date,
                amount=row.amount,
                description=row.description,
                category_id=category_id,
                business_ratio=business_ratio,
                source_type=_TRANSACTIONS_SOURCE_TYPE,
                source_hash=source_hash,
                raw_data=raw_data,
            )
            .on_conflict_do_nothing(index_elements=["source_hash"])
            .returning(Transaction.id)
        )
        inserted = session.execute(stmt).first()
        if inserted is not None:
            summary.new_transaction_count += 1
        else:
            summary.duplicate_skipped_count += 1


def import_transactions_folder(session: Session, folder: Path, as_of: datetime.date) -> ImportSummary:
    """import/transactions/配下のCSVを取り込む。対象ファイルなしは正常スキップ。"""
    summary = ImportSummary()
    for path in _list_csv_files(folder):
        _import_transactions_file(session, path, summary)
        summary.files_processed += 1
        _move_to_processed(path, as_of)
    return summary


def _import_assets_file(session: Session, path: Path, summary: ImportSummary) -> None:
    rows = parse_assets_csv(path)

    for row in rows:
        account = resolve_account(session, row.institution_label)
        if account is None:
            summary.unresolved_institution_labels.append(row.institution_label)
            continue

        if account.account_type == "loan":
            write_moneyforward_loan_snapshot(session, account, row.snapshot_date, row.current_value)
            summary.asset_snapshot_count += 1
        elif account.account_type == "securities":
            write_moneyforward_securities_snapshot(
                session, account, row.snapshot_date, row.ticker_or_name, row.current_value, row.book_value
            )
            summary.asset_snapshot_count += 1


def import_assets_folder(session: Session, folder: Path, as_of: datetime.date) -> ImportSummary:
    """import/assets/配下のCSVを取り込む。対象ファイルなしは正常スキップ。"""
    summary = ImportSummary()
    for path in _list_csv_files(folder):
        _import_assets_file(session, path, summary)
        summary.files_processed += 1
        _move_to_processed(path, as_of)
    return summary


def write_cumulative_snapshots_for_all_accounts(session: Session, as_of: datetime.date) -> int:
    """balance_method=cumulativeの全口座について当日分の残高スナップショットを書き込む。"""
    accounts = (
        session.query(Account)
        .filter(Account.tracks_balance.is_(True), Account.balance_method == "cumulative")
        .all()
    )
    for account in accounts:
        write_cumulative_snapshot(session, account, as_of)
    return len(accounts)


def run_daily_import(session: Session, as_of: datetime.date | None = None) -> ImportSummary:
    """CSV取込パイプライン全体を実行する(正規化→重複防止・カテゴリ分類→DB保存→残高スナップショット→振替検知)。"""
    as_of = as_of or datetime.date.today()

    transactions_summary = import_transactions_folder(
        session, Path(settings.import_transactions_dir), as_of
    )
    assets_summary = import_assets_folder(session, Path(settings.import_assets_dir), as_of)

    cumulative_count = write_cumulative_snapshots_for_all_accounts(session, as_of)
    transfer_count = detect_and_link_transfers(session, as_of)

    return ImportSummary(
        files_processed=transactions_summary.files_processed + assets_summary.files_processed,
        new_transaction_count=transactions_summary.new_transaction_count,
        duplicate_skipped_count=transactions_summary.duplicate_skipped_count,
        unresolved_institution_labels=(
            transactions_summary.unresolved_institution_labels + assets_summary.unresolved_institution_labels
        ),
        asset_snapshot_count=assets_summary.asset_snapshot_count + cumulative_count,
        transfer_detected_count=transfer_count,
    )
