"""日次バッチのエントリポイント(Windowsタスクスケジューラから起動想定)。

実行方法: uv run python -m app.cli.run_daily_import

最上位をtry/exceptで囲み、DB接続自体に失敗した致命的なケースではDBを経由しない
簡易Discord通知を送る(ADR 0008)。個別処理単位(CSV取込・カードメール取込・バックアップ等)の
リトライ・成否記録はapp.services.batch_orchestrator.run_daily_batchが担う。
"""

import logging
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.batch_orchestrator import run_daily_batch
from app.services.discord_notify import send_startup_failure

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    try:
        with SessionLocal() as session:
            batch_log = run_daily_batch(session)
    except Exception as exc:
        logger.exception("バッチが起動に失敗しました")
        send_startup_failure(settings.discord_webhook_url, exc)
        sys.exit(1)

    logger.info(
        "日次バッチ完了: status=%s new_transactions=%d transfers=%d",
        batch_log.status,
        batch_log.new_transaction_count,
        batch_log.transfer_detected_count,
    )
    for step in batch_log.institution_results or []:
        logger.info("  - %s: %s (%s)", step["name"], step["status"], step.get("detail") or step.get("error"))

    if batch_log.status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
