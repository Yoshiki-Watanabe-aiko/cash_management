import datetime
import decimal

import pytest
from sqlalchemy import select

from app.models import Account, Institution
from app.services import account_management
from app.services.account_management import AccountValidationError


def _institution_id(session, name: str) -> int:
    return session.execute(select(Institution.id).where(Institution.institution_name == name)).scalar_one()


def test_create_account_persists_new_row(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    account = account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座作成A",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=decimal.Decimal("100000"),
        opening_balance_date=datetime.date(2026, 7, 1),
        moneyforward_account_name=None,
        card_last4=None,
    )

    assert account.id is not None
    assert db_session.get(Account, account.id).account_name == "テスト口座作成A"


def test_create_account_rejects_unknown_institution(db_session):
    with pytest.raises(AccountValidationError):
        account_management.create_account(
            db_session,
            institution_id=999999999,
            account_name="テスト口座作成B",
            account_type="bank",
            is_business=False,
            is_active=True,
            default_business_ratio=decimal.Decimal("0"),
            tracks_balance=False,
            balance_method=None,
            opening_balance=None,
            opening_balance_date=None,
            moneyforward_account_name=None,
            card_last4=None,
        )


def test_create_account_rejects_invalid_account_type(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    with pytest.raises(AccountValidationError):
        account_management.create_account(
            db_session,
            institution_id=institution_id,
            account_name="テスト口座作成C",
            account_type="crypto",
            is_business=False,
            is_active=True,
            default_business_ratio=decimal.Decimal("0"),
            tracks_balance=False,
            balance_method=None,
            opening_balance=None,
            opening_balance_date=None,
            moneyforward_account_name=None,
            card_last4=None,
        )


def test_create_account_requires_balance_method_when_tracking_balance(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    with pytest.raises(AccountValidationError):
        account_management.create_account(
            db_session,
            institution_id=institution_id,
            account_name="テスト口座作成D",
            account_type="bank",
            is_business=False,
            is_active=True,
            default_business_ratio=decimal.Decimal("0"),
            tracks_balance=True,
            balance_method=None,
            opening_balance=None,
            opening_balance_date=None,
            moneyforward_account_name=None,
            card_last4=None,
        )


def test_create_account_requires_opening_balance_for_cumulative_method(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    with pytest.raises(AccountValidationError):
        account_management.create_account(
            db_session,
            institution_id=institution_id,
            account_name="テスト口座作成E",
            account_type="bank",
            is_business=False,
            is_active=True,
            default_business_ratio=decimal.Decimal("0"),
            tracks_balance=True,
            balance_method="cumulative",
            opening_balance=None,
            opening_balance_date=None,
            moneyforward_account_name=None,
            card_last4=None,
        )


def test_create_account_rejects_balance_method_when_not_tracking_balance(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    with pytest.raises(AccountValidationError):
        account_management.create_account(
            db_session,
            institution_id=institution_id,
            account_name="テスト口座作成F",
            account_type="credit_card",
            is_business=False,
            is_active=True,
            default_business_ratio=decimal.Decimal("100"),
            tracks_balance=False,
            balance_method="manual",
            opening_balance=None,
            opening_balance_date=None,
            moneyforward_account_name=None,
            card_last4=None,
        )


def test_update_account_toggles_is_active(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    account = account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座更新A",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=False,
        balance_method=None,
        opening_balance=None,
        opening_balance_date=None,
        moneyforward_account_name=None,
        card_last4=None,
    )

    updated = account_management.update_account(db_session, account.id, {"is_active": False})

    assert updated.is_active is False


def test_update_account_rejects_unknown_institution(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    account = account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座更新B",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=False,
        balance_method=None,
        opening_balance=None,
        opening_balance_date=None,
        moneyforward_account_name=None,
        card_last4=None,
    )

    with pytest.raises(AccountValidationError):
        account_management.update_account(db_session, account.id, {"institution_id": 999999999})


def test_update_account_returns_none_when_not_found(db_session):
    result = account_management.update_account(db_session, 999999999, {"is_active": False})
    assert result is None


@pytest.mark.parametrize(
    "field",
    [
        "institution_id",
        "account_name",
        "account_type",
        "is_business",
        "is_active",
        "default_business_ratio",
        "tracks_balance",
    ],
)
def test_update_account_rejects_null_on_not_nullable_field(db_session, field):
    institution_id = _institution_id(db_session, "楽天銀行")
    account = account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座NULL検証",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=False,
        balance_method=None,
        opening_balance=None,
        opening_balance_date=None,
        moneyforward_account_name=None,
        card_last4=None,
    )

    with pytest.raises(AccountValidationError):
        account_management.update_account(db_session, account.id, {field: None})


def test_update_account_clears_stale_opening_balance_when_balance_method_changes(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    account = account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座残高方式変更",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=decimal.Decimal("50000"),
        opening_balance_date=datetime.date(2026, 1, 1),
        moneyforward_account_name=None,
        card_last4=None,
    )

    updated = account_management.update_account(
        db_session, account.id, {"balance_method": "moneyforward"}
    )

    assert updated.opening_balance is None
    assert updated.opening_balance_date is None


def test_list_accounts_detail_returns_all_accounts(db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    account_management.create_account(
        db_session,
        institution_id=institution_id,
        account_name="テスト口座一覧A",
        account_type="bank",
        is_business=False,
        is_active=True,
        default_business_ratio=decimal.Decimal("0"),
        tracks_balance=False,
        balance_method=None,
        opening_balance=None,
        opening_balance_date=None,
        moneyforward_account_name=None,
        card_last4=None,
    )

    accounts = account_management.list_accounts_detail(db_session)

    assert any(account.account_name == "テスト口座一覧A" for account in accounts)
