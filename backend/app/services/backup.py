import calendar
import datetime
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import settings

logger = logging.getLogger(__name__)

_FILENAME_PATTERN = re.compile(r"^cash_management_(\d{4}-\d{2}-\d{2})\.dump$")


@dataclass
class BackupResult:
    file_path: Path
    deleted_count: int = 0


def _backup_filename(as_of: datetime.date) -> str:
    return f"cash_management_{as_of.isoformat()}.dump"


def run_pg_dump(as_of: datetime.date) -> Path:
    """pg_dumpをカスタム形式(-Fc)で実行し、backups/へ保存する。パスワードはコマンドライン引数ではなくPGPASSWORD環境変数で渡す。"""
    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    output_path = backup_dir / _backup_filename(as_of)

    parsed = urlsplit(settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1))
    dbname = parsed.path.lstrip("/")

    command = [
        settings.pg_dump_path,
        "-h",
        parsed.hostname or "localhost",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "",
        "-d",
        dbname,
        "-Fc",
        "-f",
        str(output_path),
    ]
    # os.environを継承しないとWindowsのネットワーク名前解決に必要な環境変数(SYSTEMROOT等)が
    # 失われ、pg_dumpがホスト名解決に失敗する。PGPASSWORDのみ追加で上書きする。
    env = {**os.environ, "PGPASSWORD": parsed.password or ""}

    subprocess.run(command, check=True, capture_output=True, env=env, text=True)  # noqa: S603
    return output_path


def _is_month_end(day: datetime.date) -> bool:
    return day.day == calendar.monthrange(day.year, day.month)[1]


def cleanup_old_backups(as_of: datetime.date) -> int:
    """直近N日分の日次バックアップ＋各月末分(1年間保持)以外を削除する(要件定義書4.3章)。"""
    backup_dir = Path(settings.backup_dir)
    if not backup_dir.exists():
        return 0

    deleted_count = 0
    for path in backup_dir.glob("cash_management_*.dump"):
        match = _FILENAME_PATTERN.match(path.name)
        if match is None:
            continue

        backup_date = datetime.date.fromisoformat(match.group(1))
        age_days = (as_of - backup_date).days

        within_daily_retention = age_days <= settings.backup_daily_retention_days
        within_month_end_retention = _is_month_end(backup_date) and age_days <= settings.backup_month_end_retention_days

        if within_daily_retention or within_month_end_retention:
            continue

        path.unlink()
        deleted_count += 1
        logger.info("期限切れバックアップを削除しました: %s", path.name)

    return deleted_count


def run_backup(as_of: datetime.date | None = None) -> BackupResult:
    """pg_dumpバックアップ実行＋世代管理削除をまとめて行う。"""
    as_of = as_of or datetime.date.today()
    file_path = run_pg_dump(as_of)
    deleted_count = cleanup_old_backups(as_of)
    return BackupResult(file_path=file_path, deleted_count=deleted_count)
