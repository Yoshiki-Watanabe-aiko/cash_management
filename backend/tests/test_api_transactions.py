import datetime
import decimal

from sqlalchemy import select

from app.models import Account, Institution, Transaction


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _make_account(session, name: str) -> Account:
    account = Account(
        institution_id=_bank_institution_id(session),
        account_name=name,
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
    )
    session.add(account)
    session.flush()
    return account


def test_get_transactions_returns_paginated_list(client, db_session):
    account = _make_account(db_session, "テストAPI取引口座")
    txn = Transaction(
        account_id=account.id,
        transaction_date=datetime.date(2026, 6, 1),
        amount=decimal.Decimal("-1000"),
        description="API一覧テスト",
        business_ratio=decimal.Decimal("0"),
        source_type="moneyforward_csv",
        source_hash="api-list-1",
    )
    db_session.add(txn)
    db_session.flush()

    response = client.get(f"/api/transactions?account_id={account.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["description"] == "API一覧テスト"
    assert body["items"][0]["is_transferred"] is False


def test_patch_transaction_updates_business_ratio(client, db_session):
    account = _make_account(db_session, "テストAPI更新口座")
    txn = Transaction(
        account_id=account.id,
        transaction_date=datetime.date(2026, 6, 1),
        amount=decimal.Decimal("-1000"),
        description="API更新テスト",
        business_ratio=decimal.Decimal("0"),
        source_type="moneyforward_csv",
        source_hash="api-patch-1",
    )
    db_session.add(txn)
    db_session.flush()

    response = client.patch(f"/api/transactions/{txn.id}", json={"business_ratio": 40})

    assert response.status_code == 200
    assert response.json()["business_ratio"] == "40"


def test_patch_transaction_returns_400_for_unknown_category_id(client, db_session):
    account = _make_account(db_session, "テストAPI不正カテゴリ口座")
    txn = Transaction(
        account_id=account.id,
        transaction_date=datetime.date(2026, 6, 1),
        amount=decimal.Decimal("-1000"),
        description="API不正カテゴリテスト",
        business_ratio=decimal.Decimal("0"),
        source_type="moneyforward_csv",
        source_hash="api-patch-bad-category",
    )
    db_session.add(txn)
    db_session.flush()

    response = client.patch(f"/api/transactions/{txn.id}", json={"category_id": 999999999})

    assert response.status_code == 400


def test_patch_transaction_returns_404_when_not_found(client):
    response = client.patch("/api/transactions/999999999", json={"business_ratio": 40})
    assert response.status_code == 404


def test_recategorize_endpoint_returns_updated_count(client):
    response = client.post("/api/transactions/recategorize")
    assert response.status_code == 200
    assert "updated_count" in response.json()
