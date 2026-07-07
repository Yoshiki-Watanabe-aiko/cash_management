"""日次CSV取込バッチのエントリポイント。

実行方法: uv run python -m app.cli.run_daily_import
"""

import logging

from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.services.card_email_pipeline import import_card_emails
from app.services.csv_import_pipeline import run_daily_import

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    with SessionLocal() as session:
        csv_summary = run_daily_import(session)
        card_summary = import_card_emails(session)
        session.commit()

    logger.info(
        "CSV取込完了: files=%d new=%d duplicate=%d snapshots=%d transfers=%d unresolved=%s",
        csv_summary.files_processed,
        csv_summary.new_transaction_count,
        csv_summary.duplicate_skipped_count,
        csv_summary.asset_snapshot_count,
        csv_summary.transfer_detected_count,
        csv_summary.unresolved_institution_labels,
    )
    logger.info(
        "カードメール取込完了: mailboxes=%d fetched=%d new=%d duplicate=%d "
        "unresolved_sender=%d no_parser=%d unresolved_account=%d last4_mismatch=%d",
        card_summary.mailboxes_processed,
        card_summary.messages_fetched,
        card_summary.new_transaction_count,
        card_summary.duplicate_skipped_count,
        card_summary.unresolved_sender_count,
        card_summary.no_parser_count,
        card_summary.unresolved_account_count,
        card_summary.last4_mismatch_count,
    )


if __name__ == "__main__":
    main()
