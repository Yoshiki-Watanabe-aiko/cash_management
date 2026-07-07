import datetime
import subprocess

from app.core import config as config_module
from app.services import backup


def test_run_pg_dump_builds_expected_command(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module.settings, "backup_dir", str(tmp_path))
    monkeypatch.setattr(config_module.settings, "pg_dump_path", "pg_dump")
    monkeypatch.setattr(
        config_module.settings,
        "database_url",
        "postgresql+psycopg://cash_user:secret@localhost:5432/cash_management",
    )

    captured = {}

    def fake_run(command, check, capture_output, env, text):
        captured["command"] = command
        captured["env"] = env

    monkeypatch.setattr(subprocess, "run", fake_run)

    output_path = backup.run_pg_dump(datetime.date(2026, 7, 8))

    assert output_path == tmp_path / "cash_management_2026-07-08.dump"
    assert captured["command"][:1] == ["pg_dump"]
    assert "-h" in captured["command"] and "localhost" in captured["command"]
    assert "cash_management" in captured["command"]
    assert captured["env"]["PGPASSWORD"] == "secret"
    assert "PATH" in captured["env"]  # os.environを継承していることの確認
    assert "secret" not in captured["command"]


def test_cleanup_old_backups_keeps_recent_daily_and_deletes_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module.settings, "backup_dir", str(tmp_path))
    monkeypatch.setattr(config_module.settings, "backup_daily_retention_days", 30)
    monkeypatch.setattr(config_module.settings, "backup_month_end_retention_days", 365)

    as_of = datetime.date(2026, 7, 8)
    recent = tmp_path / "cash_management_2026-07-01.dump"
    stale_mid_month = tmp_path / "cash_management_2026-05-15.dump"
    stale_month_end = tmp_path / "cash_management_2026-05-31.dump"
    recent.write_bytes(b"dummy")
    stale_mid_month.write_bytes(b"dummy")
    stale_month_end.write_bytes(b"dummy")

    deleted_count = backup.cleanup_old_backups(as_of)

    assert deleted_count == 1
    assert recent.exists()
    assert stale_month_end.exists()
    assert not stale_mid_month.exists()


def test_cleanup_old_backups_deletes_month_end_backup_older_than_one_year(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module.settings, "backup_dir", str(tmp_path))
    monkeypatch.setattr(config_module.settings, "backup_daily_retention_days", 30)
    monkeypatch.setattr(config_module.settings, "backup_month_end_retention_days", 365)

    as_of = datetime.date(2026, 7, 8)
    too_old_month_end = tmp_path / "cash_management_2024-01-31.dump"
    too_old_month_end.write_bytes(b"dummy")

    deleted_count = backup.cleanup_old_backups(as_of)

    assert deleted_count == 1
    assert not too_old_month_end.exists()


def test_cleanup_old_backups_returns_zero_when_dir_missing(monkeypatch, tmp_path):
    missing_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr(config_module.settings, "backup_dir", str(missing_dir))

    assert backup.cleanup_old_backups(datetime.date(2026, 7, 8)) == 0


def test_run_backup_runs_dump_then_cleanup(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module.settings, "backup_dir", str(tmp_path))

    calls = []
    monkeypatch.setattr(backup, "run_pg_dump", lambda as_of: calls.append(("dump", as_of)) or tmp_path / "x.dump")
    monkeypatch.setattr(backup, "cleanup_old_backups", lambda as_of: calls.append(("cleanup", as_of)) or 2)

    result = backup.run_backup(datetime.date(2026, 7, 8))

    assert result.file_path == tmp_path / "x.dump"
    assert result.deleted_count == 2
    assert calls == [("dump", datetime.date(2026, 7, 8)), ("cleanup", datetime.date(2026, 7, 8))]
