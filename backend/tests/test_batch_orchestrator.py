import datetime

from sqlalchemy import select

from app.core import config as config_module
from app.models import BatchLog
from app.services import backup, batch_orchestrator, discord_notify


def _configure_empty_sources(monkeypatch, tmp_path):
    txn_dir = tmp_path / "transactions"
    asset_dir = tmp_path / "assets"
    txn_dir.mkdir()
    asset_dir.mkdir()
    monkeypatch.setattr(config_module.settings, "import_transactions_dir", str(txn_dir))
    monkeypatch.setattr(config_module.settings, "import_assets_dir", str(asset_dir))
    monkeypatch.setattr(config_module.settings, "gmail_personal_address", "")
    monkeypatch.setattr(config_module.settings, "gmail_personal_app_password", "")
    monkeypatch.setattr(config_module.settings, "gmail_business_address", "")
    monkeypatch.setattr(config_module.settings, "gmail_business_app_password", "")
    monkeypatch.setattr(config_module.settings, "batch_retry_count", 1)
    monkeypatch.setattr(config_module.settings, "batch_retry_delay_seconds", 0)


def _mock_backup(monkeypatch, tmp_path):
    monkeypatch.setattr(
        backup, "run_backup", lambda as_of: backup.BackupResult(file_path=tmp_path / "x.dump", deleted_count=0)
    )


def test_run_daily_batch_all_steps_succeed(db_session, tmp_path, monkeypatch):
    _configure_empty_sources(monkeypatch, tmp_path)
    _mock_backup(monkeypatch, tmp_path)
    notified = {}
    monkeypatch.setattr(
        discord_notify,
        "send_batch_summary",
        lambda webhook_url, **kwargs: notified.update(kwargs),
    )

    batch_log = batch_orchestrator.run_daily_batch(db_session, as_of=datetime.date(2026, 7, 8))

    assert batch_log.status == "success"
    assert batch_log.new_transaction_count == 0
    assert batch_log.transfer_detected_count == 0
    assert len(batch_log.institution_results) == 7
    assert all(step["status"] == "success" for step in batch_log.institution_results)
    assert batch_log.discord_notified_at is not None
    assert notified["overall_status"] == "success"

    persisted = db_session.execute(select(BatchLog).where(BatchLog.id == batch_log.id)).scalar_one()
    assert persisted.status == "success"


def test_run_daily_batch_marks_partial_success_when_one_step_fails(db_session, tmp_path, monkeypatch):
    _configure_empty_sources(monkeypatch, tmp_path)
    _mock_backup(monkeypatch, tmp_path)
    monkeypatch.setattr(discord_notify, "send_batch_summary", lambda webhook_url, **kwargs: None)

    call_count = []

    def failing_transfer_detection(session, as_of):
        call_count.append(1)
        raise RuntimeError("振替検知の障害テスト")

    monkeypatch.setattr(batch_orchestrator, "detect_and_link_transfers", failing_transfer_detection)

    batch_log = batch_orchestrator.run_daily_batch(db_session, as_of=datetime.date(2026, 7, 8))

    assert batch_log.status == "partial_success"
    step_by_name = {step["name"]: step for step in batch_log.institution_results}
    assert step_by_name["振替検知"]["status"] == "failed"
    assert "振替検知の障害テスト" in step_by_name["振替検知"]["error"]
    assert step_by_name["MFME取引明細CSV取込"]["status"] == "success"
    assert step_by_name["カードメール取込(個人用)"]["status"] == "success"
    assert step_by_name["pg_dumpバックアップ"]["status"] == "success"
    # batch_retry_count=1のため1回のみ呼ばれる
    assert len(call_count) == 1


def test_run_daily_batch_reports_failed_csv_file_as_step_failure(db_session, tmp_path, monkeypatch):
    _configure_empty_sources(monkeypatch, tmp_path)
    _mock_backup(monkeypatch, tmp_path)
    monkeypatch.setattr(discord_notify, "send_batch_summary", lambda webhook_url, **kwargs: None)

    txn_dir = tmp_path / "transactions"
    bad_csv = (
        "計算対象,日付,内容,金額（円）,保有金融機関,大項目,中項目,メモ,振替,ID\n"
        "1,2026/07/01,壊れた行,不正な金額,どこかの銀行,,,,0,pipe-bad\n"
    )
    (txn_dir / "broken.csv").write_text(bad_csv, encoding="utf-8-sig")

    batch_log = batch_orchestrator.run_daily_batch(db_session, as_of=datetime.date(2026, 7, 8))

    assert batch_log.status == "partial_success"
    step_by_name = {step["name"]: step for step in batch_log.institution_results}
    assert step_by_name["MFME取引明細CSV取込"]["status"] == "failed"
    assert "broken.csv" in step_by_name["MFME取引明細CSV取込"]["error"]
    assert step_by_name["MFME資産評価CSV取込"]["status"] == "success"


def test_run_daily_batch_marks_failed_when_all_steps_fail(db_session, tmp_path, monkeypatch):
    _configure_empty_sources(monkeypatch, tmp_path)
    monkeypatch.setattr(discord_notify, "send_batch_summary", lambda webhook_url, **kwargs: None)

    def boom(*args, **kwargs):
        raise RuntimeError("全滅テスト")

    monkeypatch.setattr(batch_orchestrator, "import_transactions_folder", boom)
    monkeypatch.setattr(batch_orchestrator, "import_assets_folder", boom)
    monkeypatch.setattr(batch_orchestrator, "write_cumulative_snapshots_for_all_accounts", boom)
    monkeypatch.setattr(batch_orchestrator, "detect_and_link_transfers", boom)
    monkeypatch.setattr(batch_orchestrator, "import_personal_card_emails", boom)
    monkeypatch.setattr(batch_orchestrator, "import_business_card_emails", boom)
    monkeypatch.setattr(backup, "run_backup", boom)

    batch_log = batch_orchestrator.run_daily_batch(db_session, as_of=datetime.date(2026, 7, 8))

    assert batch_log.status == "failed"
    assert all(step["status"] == "failed" for step in batch_log.institution_results)
