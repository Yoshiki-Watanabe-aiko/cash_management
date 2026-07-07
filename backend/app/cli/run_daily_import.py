"""日次CSV取込バッチのエントリポイント。

実行方法: uv run python -m app.cli.run_daily_import
"""

import logging

from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.csv_import_pipeline import run_daily_import

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    with SessionLocal() as session:
        summary = run_daily_import(session)
        session.commit()

    logger.info(
        "取込完了: files=%d new=%d duplicate=%d snapshots=%d transfers=%d unresolved=%s",
        summary.files_processed,
        summary.new_transaction_count,
        summary.duplicate_skipped_count,
        summary.asset_snapshot_count,
        summary.transfer_detected_count,
        summary.unresolved_institution_labels,
    )


if __name__ == "__main__":
    main()
