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


def test_post_transaction_creates_manual_transaction(client, db_session):
    account = _make_account(db_session, "テストAPI手動登録口座")

    response = client.post(
        "/api/transactions",
        json={
            "account_id": account.id,
            "transaction_date": "2026-07-01",
            "amount": "-500",
            "description": "現金払い(手動登録)",
            "business_ratio": 0,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "manual"
    assert body["description"] == "現金払い(手動登録)"


def test_post_transaction_without_account_for_cash_payment(client):
    response = client.post(
        "/api/transactions",
        json={
            "transaction_date": "2026-07-01",
            "amount": "-1000",
            "description": "現金(財布)払い",
        },
    )

    assert response.status_code == 201
    assert response.json()["account_id"] is None


def test_post_transaction_returns_400_for_unknown_account_id(client):
    response = client.post(
        "/api/transactions",
        json={
            "account_id": 999999999,
            "transaction_date": "2026-07-01",
            "amount": "-100",
            "description": "不正口座",
        },
    )

    assert response.status_code == 400


def test_post_transaction_returns_400_for_zero_amount(client):
    response = client.post(
        "/api/transactions",
        json={
            "transaction_date": "2026-07-01",
            "amount": "0",
            "description": "金額ゼロ",
        },
    )

    assert response.status_code == 400
