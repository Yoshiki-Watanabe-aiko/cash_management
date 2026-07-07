import datetime
import decimal

from sqlalchemy import select

from app.models import Account, AssetClass, AssetSnapshot, Institution, Transaction
from app.services.balance_snapshot import (
    compute_cumulative_balance,
    write_cumulative_snapshot,
    write_moneyforward_loan_snapshot,
    write_moneyforward_securities_snapshot,
)


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _securities_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天証券")
    ).scalar_one()


def _asset_class_name(session, asset_class_id: int) -> str:
    return session.execute(
        select(AssetClass.asset_class_name).where(AssetClass.id == asset_class_id)
    ).scalar_one()


def test_compute_cumulative_balance_adds_transactions_to_opening_balance(db_session):
    account = Account(
        institution_id=_bank_institution_id(db_session),
        account_name="テスト累積残高口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=decimal.Decimal("10000"),
        opening_balance_date=datetime.date(2026, 6, 1),
    )
    db_session.add(account)
    db_session.flush()

    db_session.add_all(
        [
            Transaction(
                account_id=account.id,
                transaction_date=datetime.date(2026, 6, 15),
                amount=decimal.Decimal("-1000"),
                description="出金",
                business_ratio=0,
                source_type="moneyforward_csv",
                source_hash="bal-test-1",
            ),
            Transaction(
                account_id=account.id,
                transaction_date=datetime.date(2026, 7, 1),
                amount=decimal.Decimal("500"),
                description="入金",
                business_ratio=0,
                source_type="moneyforward_csv",
                source_hash="bal-test-2",
            ),
        ]
    )
    db_session.flush()

    balance = compute_cumulative_balance(db_session, account, datetime.date(2026, 7, 1))
    assert balance == decimal.Decimal("9500")


def test_write_cumulative_snapshot_upserts_asset_snapshot(db_session):
    account = Account(
        institution_id=_bank_institution_id(db_session),
        account_name="テスト累積スナップショット口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=decimal.Decimal("5000"),
        opening_balance_date=datetime.date(2026, 6, 1),
    )
    db_session.add(account)
    db_session.flush()

    as_of = datetime.date(2026, 7, 1)
    write_cumulative_snapshot(db_session, account, as_of)
    db_session.flush()

    snapshot = db_session.execute(
        select(AssetSnapshot).where(
            AssetSnapshot.account_id == account.id, AssetSnapshot.snapshot_date == as_of
        )
    ).scalar_one()
    assert snapshot.current_value == decimal.Decimal("5000")
    assert snapshot.ticker_or_name == account.account_name
    assert snapshot.source_type == "cumulative"
    assert _asset_class_name(db_session, snapshot.asset_class_id) == "現金"

    # 同日に再度書き込んでも1行に更新される(UPSERT)こと
    write_cumulative_snapshot(db_session, account, as_of)
    db_session.flush()
    count = db_session.execute(
        select(AssetSnapshot).where(
            AssetSnapshot.account_id == account.id, AssetSnapshot.snapshot_date == as_of
        )
    ).scalars().all()
    assert len(count) == 1


def test_write_moneyforward_loan_snapshot_stores_negative_value(db_session):
    account = Account(
        institution_id=_bank_institution_id(db_session),
        account_name="テストローン口座",
        account_type="loan",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="moneyforward",
    )
    db_session.add(account)
    db_session.flush()

    as_of = datetime.date(2026, 7, 1)
    write_moneyforward_loan_snapshot(db_session, account, as_of, decimal.Decimal("2000000"))
    db_session.flush()

    snapshot = db_session.execute(
        select(AssetSnapshot).where(AssetSnapshot.account_id == account.id)
    ).scalar_one()
    assert snapshot.current_value == decimal.Decimal("-2000000")
    assert _asset_class_name(db_session, snapshot.asset_class_id) == "ローン"


def test_write_moneyforward_securities_snapshot_classifies_fund_by_keyword(db_session):
    account = Account(
        institution_id=_securities_institution_id(db_session),
        account_name="テスト証券口座",
        account_type="securities",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="moneyforward",
    )
    db_session.add(account)
    db_session.flush()

    as_of = datetime.date(2026, 7, 1)
    write_moneyforward_securities_snapshot(
        db_session, account, as_of, "全世界株式インデックスファンド", decimal.Decimal("500000"), decimal.Decimal("450000")
    )
    db_session.flush()

    snapshot = db_session.execute(
        select(AssetSnapshot).where(AssetSnapshot.account_id == account.id)
    ).scalar_one()
    assert _asset_class_name(db_session, snapshot.asset_class_id) == "投資信託"
    assert snapshot.current_value == decimal.Decimal("500000")
    assert snapshot.book_value == decimal.Decimal("450000")


def test_write_moneyforward_securities_snapshot_defaults_to_stock(db_session):
    account = Account(
        institution_id=_securities_institution_id(db_session),
        account_name="テスト証券口座2",
        account_type="securities",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="moneyforward",
    )
    db_session.add(account)
    db_session.flush()

    as_of = datetime.date(2026, 7, 1)
    write_moneyforward_securities_snapshot(
        db_session, account, as_of, "トヨタ自動車", decimal.Decimal("300000"), None
    )
    db_session.flush()

    snapshot = db_session.execute(
        select(AssetSnapshot).where(AssetSnapshot.account_id == account.id)
    ).scalar_one()
    assert _asset_class_name(db_session, snapshot.asset_class_id) == "国内株式"
