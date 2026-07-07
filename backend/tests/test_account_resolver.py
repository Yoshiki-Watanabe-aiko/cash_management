from sqlalchemy import select

from app.models import Account, Institution
from app.services.account_resolver import resolve_account, resolve_card_account, resolve_institution_by_sender


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _credit_card_institution(session, name: str = "楽天カード") -> Institution:
    return session.execute(
        select(Institution).where(Institution.institution_name == name)
    ).scalar_one()


def test_resolves_by_moneyforward_account_name(db_session):
    institution_id = _bank_institution_id(db_session)
    account = Account(
        institution_id=institution_id,
        account_name="テスト銀行個人口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        moneyforward_account_name="楽天銀行(個人)",
    )
    db_session.add(account)
    db_session.flush()

    resolved = resolve_account(db_session, "楽天銀行(個人)")
    assert resolved is not None
    assert resolved.id == account.id


def test_falls_back_to_account_name_when_mf_name_unset(db_session):
    institution_id = _bank_institution_id(db_session)
    account = Account(
        institution_id=institution_id,
        account_name="テスト銀行フォールバック口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
    )
    db_session.add(account)
    db_session.flush()

    resolved = resolve_account(db_session, "テスト銀行フォールバック口座")
    assert resolved is not None
    assert resolved.id == account.id


def test_ignores_fullwidth_and_halfwidth_space_differences(db_session):
    institution_id = _bank_institution_id(db_session)
    account = Account(
        institution_id=institution_id,
        account_name="テスト銀行　個人",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
    )
    db_session.add(account)
    db_session.flush()

    resolved = resolve_account(db_session, "テスト銀行 個人")
    assert resolved is not None
    assert resolved.id == account.id


def test_returns_none_when_inactive(db_session):
    institution_id = _bank_institution_id(db_session)
    account = Account(
        institution_id=institution_id,
        account_name="テスト銀行休眠口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        is_active=False,
    )
    db_session.add(account)
    db_session.flush()

    assert resolve_account(db_session, "テスト銀行休眠口座") is None


def test_returns_none_when_no_match(db_session):
    assert resolve_account(db_session, "存在しない口座名") is None


def test_resolve_institution_by_sender_matches_case_insensitively(db_session):
    institution = _credit_card_institution(db_session)
    institution.card_alert_sender_email = "Alert@Example.co.jp"
    db_session.flush()

    resolved = resolve_institution_by_sender(db_session, "alert@example.co.jp")
    assert resolved is not None
    assert resolved.id == institution.id


def test_resolve_institution_by_sender_returns_none_when_unset(db_session):
    assert resolve_institution_by_sender(db_session, "unknown@example.com") is None


def test_resolve_card_account_matches_institution_and_mailbox(db_session):
    institution = _credit_card_institution(db_session, "PayPayカード")
    personal_account = Account(
        institution_id=institution.id,
        account_name="PayPayカード 個人",
        account_type="credit_card",
        is_business=False,
        default_business_ratio=0,
    )
    business_account = Account(
        institution_id=institution.id,
        account_name="PayPayカード 事業",
        account_type="credit_card",
        is_business=True,
        default_business_ratio=100,
    )
    db_session.add_all([personal_account, business_account])
    db_session.flush()

    resolved_personal = resolve_card_account(db_session, institution.id, False)
    resolved_business = resolve_card_account(db_session, institution.id, True)

    assert resolved_personal is not None and resolved_personal.id == personal_account.id
    assert resolved_business is not None and resolved_business.id == business_account.id


def test_resolve_card_account_returns_none_when_no_match(db_session):
    institution = _credit_card_institution(db_session, "セゾンカード")
    assert resolve_card_account(db_session, institution.id, False) is None
