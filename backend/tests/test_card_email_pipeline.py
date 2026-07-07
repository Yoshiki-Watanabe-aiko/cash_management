import datetime
import decimal
import email.message

from sqlalchemy import select

from app.core import config as config_module
from app.models import Account, Institution, Transaction
from app.schemas.card_email import ParsedCardTransaction
from app.services.card_email_pipeline import import_card_emails
from app.services.card_parsers.registry import _PARSERS, register_parser
from app.services.mail_client import FetchedMail


class _StubParser:
    def __init__(self, result: ParsedCardTransaction | None):
        self._result = result

    def parse(self, message):
        return self._result


def _credit_card_institution(session, name: str) -> Institution:
    return session.execute(
        select(Institution).where(Institution.institution_name == name)
    ).scalar_one()


def _make_personal_card_account(session, institution_id: int, name: str, last4: str | None = None) -> Account:
    account = Account(
        institution_id=institution_id,
        account_name=name,
        account_type="credit_card",
        is_business=False,
        default_business_ratio=0,
        card_last4=last4,
    )
    session.add(account)
    session.flush()
    return account


def _fake_mail(from_address: str, message_id: str) -> FetchedMail:
    return FetchedMail(message=email.message.EmailMessage(), from_address=from_address, message_id=message_id)


def _mock_personal_mailbox_only(monkeypatch, mails: list[FetchedMail]) -> None:
    monkeypatch.setattr(
        "app.services.card_email_pipeline.fetch_recent_messages",
        lambda address, app_password, since, mailbox="INBOX": mails,
    )
    monkeypatch.setattr(config_module.settings, "gmail_personal_address", "me@gmail.com")
    monkeypatch.setattr(config_module.settings, "gmail_personal_app_password", "app-pass")
    monkeypatch.setattr(config_module.settings, "gmail_business_address", "")
    monkeypatch.setattr(config_module.settings, "gmail_business_app_password", "")


def test_import_card_emails_inserts_transaction(db_session, monkeypatch):
    institution = _credit_card_institution(db_session, "楽天カード")
    institution.card_alert_sender_email = "alerts@rakuten-card.example"
    db_session.flush()
    account = _make_personal_card_account(db_session, institution.id, "パイプラインカード個人A", last4="1234")

    parsed = ParsedCardTransaction(
        transaction_date=datetime.date(2026, 7, 5),
        amount=decimal.Decimal("-3000"),
        description="テストストア",
        message_id="<card-1@example>",
        card_last4="1234",
    )
    register_parser(institution.institution_name, _StubParser(parsed))
    _mock_personal_mailbox_only(
        monkeypatch, [_fake_mail("alerts@rakuten-card.example", "<card-1@example>")]
    )

    try:
        summary = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))
    finally:
        _PARSERS.pop(institution.institution_name, None)

    assert summary.new_transaction_count == 1
    assert summary.duplicate_skipped_count == 0
    assert summary.last4_mismatch_count == 0

    txn = db_session.execute(
        select(Transaction).where(Transaction.account_id == account.id)
    ).scalar_one()
    assert txn.amount == decimal.Decimal("-3000")
    assert txn.description == "テストストア"
    assert txn.source_type == "gmail_imap"


def test_import_card_emails_skips_duplicate_on_rerun(db_session, monkeypatch):
    institution = _credit_card_institution(db_session, "EPOSカード")
    institution.card_alert_sender_email = "alerts@epos.example"
    db_session.flush()
    _make_personal_card_account(db_session, institution.id, "パイプラインカード個人B")

    parsed = ParsedCardTransaction(
        transaction_date=datetime.date(2026, 7, 5),
        amount=decimal.Decimal("-1500"),
        description="重複テスト店",
        message_id="<card-dup@example>",
    )
    register_parser(institution.institution_name, _StubParser(parsed))
    _mock_personal_mailbox_only(monkeypatch, [_fake_mail("alerts@epos.example", "<card-dup@example>")])

    try:
        first = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))
        db_session.flush()
        second = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))
    finally:
        _PARSERS.pop(institution.institution_name, None)

    assert first.new_transaction_count == 1
    assert second.new_transaction_count == 0
    assert second.duplicate_skipped_count == 1


def test_import_card_emails_counts_unresolved_sender(db_session, monkeypatch):
    _mock_personal_mailbox_only(monkeypatch, [_fake_mail("unknown@nowhere.example", "<card-x@example>")])

    summary = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))

    assert summary.unresolved_sender_count == 1
    assert "unknown@nowhere.example" in summary.unresolved_senders
    assert summary.new_transaction_count == 0


def test_import_card_emails_counts_no_parser_registered(db_session, monkeypatch):
    institution = _credit_card_institution(db_session, "セゾンカード")
    institution.card_alert_sender_email = "alerts@saison.example"
    db_session.flush()
    _make_personal_card_account(db_session, institution.id, "パイプラインカード個人C")

    _mock_personal_mailbox_only(monkeypatch, [_fake_mail("alerts@saison.example", "<card-y@example>")])

    summary = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))

    assert summary.no_parser_count == 1
    assert institution.institution_name in summary.no_parser_institutions
    assert summary.new_transaction_count == 0


def test_import_card_emails_counts_unresolved_account_when_no_matching_mailbox_account(db_session, monkeypatch):
    institution = _credit_card_institution(db_session, "viewカード")
    institution.card_alert_sender_email = "alerts@view-card.example"
    db_session.flush()
    # 個人用メールボックスからの受信だが、事業用口座しか登録されていないケース
    business_only_account = Account(
        institution_id=institution.id,
        account_name="viewカード 事業のみ",
        account_type="credit_card",
        is_business=True,
        default_business_ratio=100,
    )
    db_session.add(business_only_account)
    db_session.flush()

    parsed = ParsedCardTransaction(
        transaction_date=datetime.date(2026, 7, 5),
        amount=decimal.Decimal("-500"),
        description="口座未解決テスト店",
        message_id="<card-noaccount@example>",
    )
    register_parser(institution.institution_name, _StubParser(parsed))
    _mock_personal_mailbox_only(
        monkeypatch, [_fake_mail("alerts@view-card.example", "<card-noaccount@example>")]
    )

    try:
        summary = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))
    finally:
        _PARSERS.pop(institution.institution_name, None)

    assert summary.unresolved_account_count == 1
    assert summary.new_transaction_count == 0


def test_import_card_emails_flags_last4_mismatch_but_still_inserts(db_session, monkeypatch):
    institution = _credit_card_institution(db_session, "イオンカード")
    institution.card_alert_sender_email = "alerts@aeon-card.example"
    db_session.flush()
    _make_personal_card_account(db_session, institution.id, "パイプラインカード個人D", last4="9999")

    parsed = ParsedCardTransaction(
        transaction_date=datetime.date(2026, 7, 5),
        amount=decimal.Decimal("-2000"),
        description="不一致テスト店",
        message_id="<card-mismatch@example>",
        card_last4="0000",
    )
    register_parser(institution.institution_name, _StubParser(parsed))
    _mock_personal_mailbox_only(
        monkeypatch, [_fake_mail("alerts@aeon-card.example", "<card-mismatch@example>")]
    )

    try:
        summary = import_card_emails(db_session, as_of=datetime.date(2026, 7, 8))
    finally:
        _PARSERS.pop(institution.institution_name, None)

    assert summary.new_transaction_count == 1
    assert summary.last4_mismatch_count == 1

    txn = db_session.execute(
        select(Transaction).where(Transaction.description == "不一致テスト店")
    ).scalar_one()
    assert txn.raw_data["card_last4_mismatch"] is True
