import dataclasses
import datetime
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BatchLog
from app.services import backup, discord_notify
from app.services.card_email_pipeline import import_business_card_emails, import_personal_card_emails
from app.services.csv_import_pipeline import (
    detect_and_link_transfers,
    import_assets_folder,
    import_transactions_folder,
    write_cumulative_snapshots_for_all_accounts,
)
from app.services.retry import run_with_retry

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class StepOutcome:
    """1処理単位が成功した際の詳細(サマリー文言と件数集計への寄与分)。"""

    detail: str
    new_transaction_count: int = 0
    transfer_detected_count: int = 0


@dataclasses.dataclass
class StepResult:
    name: str
    status: str  # success / failed
    detail: str = ""
    error: str | None = None
    new_transaction_count: int = 0
    transfer_detected_count: int = 0

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail, "error": self.error}


def _run_step(session: Session, name: str, func) -> StepResult:
    """1処理単位をSAVEPOINTで囲み、軽量リトライ(既定3回)を行う(ADR 0008)。

    失敗時はSAVEPOINTをロールバックしてセッションを健全な状態に戻し、
    他のステップの処理を継続できるようにする。
    """

    def attempt() -> StepOutcome:
        with session.begin_nested():
            return func()

    try:
        outcome = run_with_retry(
            attempt,
            step_name=name,
            retries=settings.batch_retry_count,
            delay_seconds=settings.batch_retry_delay_seconds,
        )
        return StepResult(
            name=name,
            status="success",
            detail=outcome.detail,
            new_transaction_count=outcome.new_transaction_count,
            transfer_detected_count=outcome.transfer_detected_count,
        )
    except Exception as exc:  # noqa: BLE001 - ステップ単位の障害分離のため意図的に広く捕捉
        logger.exception("%s: リトライしても失敗しました", name)
        return StepResult(name=name, status="failed", error=str(exc))


def _run_transactions_csv_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        summary = import_transactions_folder(session, Path(settings.import_transactions_dir), as_of)
        if summary.failed_files:
            raise RuntimeError(f"失敗ファイル: {', '.join(summary.failed_files)}")
        detail = (
            f"ファイル{summary.files_processed}件・新規{summary.new_transaction_count}件・"
            f"重複{summary.duplicate_skipped_count}件"
        )
        return StepOutcome(detail=detail, new_transaction_count=summary.new_transaction_count)

    return _run_step(session, "MFME取引明細CSV取込", run)


def _run_assets_csv_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        summary = import_assets_folder(session, Path(settings.import_assets_dir), as_of)
        if summary.failed_files:
            raise RuntimeError(f"失敗ファイル: {', '.join(summary.failed_files)}")
        detail = f"ファイル{summary.files_processed}件・スナップショット{summary.asset_snapshot_count}件"
        return StepOutcome(detail=detail)

    return _run_step(session, "MFME資産評価CSV取込", run)


def _run_cumulative_snapshot_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        count = write_cumulative_snapshots_for_all_accounts(session, as_of)
        return StepOutcome(detail=f"{count}口座")

    return _run_step(session, "残高スナップショット(累積方式)", run)


def _run_transfer_detection_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        count = detect_and_link_transfers(session, as_of)
        return StepOutcome(detail=f"{count}件", transfer_detected_count=count)

    return _run_step(session, "振替検知", run)


def _run_personal_card_email_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        summary = import_personal_card_emails(session, as_of)
        detail = (
            f"メールボックス{summary.mailboxes_processed}件・取得{summary.messages_fetched}件・"
            f"新規{summary.new_transaction_count}件・解析エラー{summary.parse_error_count}件"
        )
        return StepOutcome(detail=detail, new_transaction_count=summary.new_transaction_count)

    return _run_step(session, "カードメール取込(個人用)", run)


def _run_business_card_email_step(session: Session, as_of: datetime.date) -> StepResult:
    def run() -> StepOutcome:
        summary = import_business_card_emails(session, as_of)
        detail = (
            f"メールボックス{summary.mailboxes_processed}件・取得{summary.messages_fetched}件・"
            f"新規{summary.new_transaction_count}件・解析エラー{summary.parse_error_count}件"
        )
        return StepOutcome(detail=detail, new_transaction_count=summary.new_transaction_count)

    return _run_step(session, "カードメール取込(事業用)", run)


def _run_backup_step(as_of: datetime.date) -> StepResult:
    """pg_dumpはDBセッションを使わないため、SAVEPOINT不要のシンプルなリトライのみ行う。"""

    def run() -> StepOutcome:
        result = backup.run_backup(as_of)
        return StepOutcome(detail=f"{result.file_path.name}・期限切れ削除{result.deleted_count}件")

    name = "pg_dumpバックアップ"
    try:
        outcome = run_with_retry(
            run,
            step_name=name,
            retries=settings.batch_retry_count,
            delay_seconds=settings.batch_retry_delay_seconds,
        )
        return StepResult(name=name, status="success", detail=outcome.detail)
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s: リトライしても失敗しました", name)
        return StepResult(name=name, status="failed", error=str(exc))


def _overall_status(step_results: list[StepResult]) -> str:
    statuses = {step.status for step in step_results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses:
        return "partial_success"
    return "failed"


def run_daily_batch(session: Session, as_of: datetime.date | None = None) -> BatchLog:
    """日次バッチ全体を実行する。各処理単位を独立したtry/except・リトライで囲み、
    結果をt_batch_logsへ記録した上でDiscordへサマリー通知する(要件定義書4.3章、ADR 0008)。
    """
    as_of = as_of or datetime.date.today()
    started_at = datetime.datetime.now(datetime.UTC)

    step_results = [
        _run_transactions_csv_step(session, as_of),
        _run_assets_csv_step(session, as_of),
        _run_cumulative_snapshot_step(session, as_of),
        _run_transfer_detection_step(session, as_of),
        _run_personal_card_email_step(session, as_of),
        _run_business_card_email_step(session, as_of),
        _run_backup_step(as_of),
    ]

    new_transaction_count = sum(step.new_transaction_count for step in step_results)
    transfer_detected_count = sum(step.transfer_detected_count for step in step_results)
    overall_status = _overall_status(step_results)

    batch_log = BatchLog(
        run_date=as_of,
        started_at=started_at,
        finished_at=datetime.datetime.now(datetime.UTC),
        status=overall_status,
        new_transaction_count=new_transaction_count,
        transfer_detected_count=transfer_detected_count,
        institution_results=[step.as_dict() for step in step_results],
    )
    session.add(batch_log)
    session.commit()

    discord_notify.send_batch_summary(
        settings.discord_webhook_url,
        run_date=as_of.isoformat(),
        overall_status=overall_status,
        step_results=[step.as_dict() for step in step_results],
        new_transaction_count=new_transaction_count,
        transfer_detected_count=transfer_detected_count,
    )
    batch_log.discord_notified_at = datetime.datetime.now(datetime.UTC)
    session.commit()

    return batch_log
