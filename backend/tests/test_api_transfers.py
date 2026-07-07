import datetime
import decimal

from sqlalchemy import select

from app.models import Account, Institution, Transaction, Transfer


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


def _make_transaction(session, account_id: int, d: datetime.date, amount, description: str, hash_suffix: str) -> Transaction:
    txn = Transaction(
        account_id=account_id,
        transaction_date=d,
        amount=amount,
        description=description,
        business_ratio=decimal.Decimal("0"),
        source_type="moneyforward_csv",
        source_hash=f"api-transfer-test-{hash_suffix}",
    )
    session.add(txn)
    session.flush()
    return txn


def test_post_transfer_creates_manual_link(client, db_session):
    account_a = _make_account(db_session, "テストAPI振替口座A")
    account_b = _make_account(db_session, "テストAPI振替口座B")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-5000"), "出金", "api-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("5000"), "入金", "api-in")

    response = client.post(
        "/api/transfers", json={"from_transaction_id": txn_out.id, "to_transaction_id": txn_in.id}
    )

    assert response.status_code == 201
    assert response.json()["match_confidence"] == "manual"


def test_post_transfer_returns_400_on_amount_mismatch(client, db_session):
    account_a = _make_account(db_session, "テストAPI振替口座C")
    account_b = _make_account(db_session, "テストAPI振替口座D")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-5000"), "出金", "api-mismatch-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("4000"), "入金", "api-mismatch-in")

    response = client.post(
        "/api/transfers", json={"from_transaction_id": txn_out.id, "to_transaction_id": txn_in.id}
    )

    assert response.status_code == 400


def test_delete_transfer_removes_link(client, db_session):
    account_a = _make_account(db_session, "テストAPI振替解除口座A")
    account_b = _make_account(db_session, "テストAPI振替解除口座B")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-5000"), "出金", "api-del-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("5000"), "入金", "api-del-in")
    transfer = Transfer(from_transaction_id=txn_out.id, to_transaction_id=txn_in.id, match_confidence="manual")
    db_session.add(transfer)
    db_session.flush()

    response = client.delete(f"/api/transfers/{transfer.id}")

    assert response.status_code == 204
    assert db_session.get(Transfer, transfer.id) is None


def test_delete_transfer_returns_404_when_not_found(client):
    response = client.delete("/api/transfers/999999999")
    assert response.status_code == 404


def test_get_unlinked_candidates_returns_only_unlinked(client, db_session):
    account = _make_account(db_session, "テストAPI候補口座")
    day = datetime.date(2026, 6, 1)
    unlinked = _make_transaction(db_session, account.id, day, decimal.Decimal("-1000"), "未リンク", "api-cand")

    response = client.get(f"/api/transfers/unlinked-candidates?as_of={day.isoformat()}")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert unlinked.id in ids
