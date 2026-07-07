import datetime
import logging
from dataclasses import dataclass, field

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Transaction
from app.services.account_resolver import resolve_card_account, resolve_institution_by_sender
from app.services.card_parsers.registry import find_parser
from app.services.categorization import categorize
from app.services.dedup import compute_source_hash
from app.services.mail_client import fetch_recent_messages

logger = logging.getLogger(__name__)

_SOURCE_TYPE = "gmail_imap"
_FETCH_WINDOW_DAYS = 3
"""既読フラグに依存せず直近N日分を毎回再取得し、source_hashで重複排除する(ADR 0010)。"""


@dataclass
class CardEmailImportSummary:
    mailboxes_processed: int = 0
    messages_fetched: int = 0
    new_transaction_count: int = 0
    duplicate_skipped_count: int = 0
    unresolved_sender_count: int = 0
    no_parser_count: int = 0
    unresolved_account_count: int = 0
    last4_mismatch_count: int = 0
    parse_error_count: int = 0
    unresolved_senders: list[str] = field(default_factory=list)
    no_parser_institutions: list[str] = field(default_factory=list)


def _import_mailbox(
    session: Session,
    address: str,
    app_password: str,
    is_business: bool,
    as_of: datetime.date,
    summary: CardEmailImportSummary,
) -> None:
    if not address or not app_password:
        return

    since = as_of - datetime.timedelta(days=_FETCH_WINDOW_DAYS)
    mails = fetch_recent_messages(address, app_password, since)
    summary.mailboxes_processed += 1
    summary.messages_fetched += len(mails)

    for mail in mails:
        try:
            with session.begin_nested():
                _import_mail(session, mail, is_business=is_business, summary=summary)
        except Exception:
            summary.parse_error_count += 1
            logger.exception(
                "カードメールの取込に失敗しました(message_id=%s)。このメールをスキップし処理を継続します",
                mail.message_id,
            )


def _import_mail(session: Session, mail, *, is_business: bool, summary: CardEmailImportSummary) -> None:
    """1通分のカードメール取込。SAVEPOINTで囲まれ、例外は呼び出し元(_import_mailbox)でメール単位に隔離する。"""
    institution = resolve_institution_by_sender(session, mail.from_address)
    if institution is None:
        summary.unresolved_sender_count += 1
        if mail.from_address not in summary.unresolved_senders:
            summary.unresolved_senders.append(mail.from_address)
        return

    parser = find_parser(institution.institution_name)
    if parser is None:
        summary.no_parser_count += 1
        if institution.institution_name not in summary.no_parser_institutions:
            summary.no_parser_institutions.append(institution.institution_name)
        return

    parsed = parser.parse(mail.message)
    if parsed is None:
        return

    account = resolve_card_account(session, institution.id, is_business)
    if account is None:
        summary.unresolved_account_count += 1
        return

    last4_mismatch = bool(
        account.card_last4 and parsed.card_last4 and account.card_last4 != parsed.card_last4
    )
    if last4_mismatch:
        summary.last4_mismatch_count += 1

    category_id = categorize(session, parsed.description)
    source_hash = compute_source_hash(
        account.id, parsed.transaction_date, parsed.amount, parsed.description, parsed.message_id
    )
    raw_data = {
        "from_address": mail.from_address,
        "message_id": parsed.message_id,
        "card_last4": parsed.card_last4,
        "card_last4_mismatch": last4_mismatch,
    }

    stmt = (
        pg_insert(Transaction)
        .values(
            account_id=account.id,
            transaction_date=parsed.transaction_date,
            amount=parsed.amount,
            description=parsed.description,
            category_id=category_id,
            business_ratio=account.default_business_ratio,
            source_type=_SOURCE_TYPE,
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


def import_personal_card_emails(session: Session, as_of: datetime.date | None = None) -> CardEmailImportSummary:
    """個人用Gmailメールボックスのみを取込む。事業用メールボックスの障害から独立させるため分離(ADR 0008)。"""
    as_of = as_of or datetime.date.today()
    summary = CardEmailImportSummary()
    _import_mailbox(
        session, settings.gmail_personal_address, settings.gmail_personal_app_password, False, as_of, summary
    )
    return summary


def import_business_card_emails(session: Session, as_of: datetime.date | None = None) -> CardEmailImportSummary:
    """事業用Gmailメールボックスのみを取込む。個人用メールボックスの障害から独立させるため分離(ADR 0008)。"""
    as_of = as_of or datetime.date.today()
    summary = CardEmailImportSummary()
    _import_mailbox(
        session, settings.gmail_business_address, settings.gmail_business_app_password, True, as_of, summary
    )
    return summary


def import_card_emails(session: Session, as_of: datetime.date | None = None) -> CardEmailImportSummary:
    """個人用・事業用の両メールボックスをまとめて取込む(後方互換用。日次バッチはbatch_orchestratorが両者を独立して呼び出す)。"""
    as_of = as_of or datetime.date.today()
    summary = CardEmailImportSummary()

    _import_mailbox(
        session, settings.gmail_personal_address, settings.gmail_personal_app_password, False, as_of, summary
    )
    _import_mailbox(
        session, settings.gmail_business_address, settings.gmail_business_app_password, True, as_of, summary
    )

    return summary
