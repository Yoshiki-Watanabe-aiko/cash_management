import datetime
import decimal

import pytest
from sqlalchemy import select

from app.models import Account, Institution, Transaction, Transfer
from app.services import transfer_management


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
        source_hash=f"transfer-mgmt-test-{hash_suffix}",
    )
    session.add(txn)
    session.flush()
    return txn


def test_create_manual_transfer_link_succeeds_without_description_match(db_session):
    account_a = _make_account(db_session, "テスト手動振替口座A")
    account_b = _make_account(db_session, "テスト手動振替口座B")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-8000"), "コンビニ", "manual-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("8000"), "入金", "manual-in")

    transfer = transfer_management.create_manual_transfer_link(db_session, txn_out.id, txn_in.id)

    assert transfer.match_confidence == "manual"
    persisted = db_session.execute(select(Transfer).where(Transfer.id == transfer.id)).scalar_one()
    assert persisted.from_transaction_id == txn_out.id
    assert persisted.to_transaction_id == txn_in.id


def test_create_manual_transfer_link_rejects_same_transaction(db_session):
    account = _make_account(db_session, "テスト手動振替口座J")
    txn = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), decimal.Decimal("-1000"), "自己", "same-txn")

    with pytest.raises(transfer_management.TransferLinkError):
        transfer_management.create_manual_transfer_link(db_session, txn.id, txn.id)


def test_create_manual_transfer_link_rejects_missing_transaction(db_session):
    account = _make_account(db_session, "テスト手動振替口座K")
    txn = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), decimal.Decimal("-1000"), "存在確認", "missing-txn")

    with pytest.raises(transfer_management.TransferLinkError):
        transfer_management.create_manual_transfer_link(db_session, txn.id, 999999999)


def test_create_manual_transfer_link_rejects_amount_mismatch(db_session):
    account_a = _make_account(db_session, "テスト手動振替口座C")
    account_b = _make_account(db_session, "テスト手動振替口座D")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-8000"), "出金", "mismatch-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("7000"), "入金", "mismatch-in")

    with pytest.raises(transfer_management.TransferLinkError):
        transfer_management.create_manual_transfer_link(db_session, txn_out.id, txn_in.id)


def test_create_manual_transfer_link_rejects_beyond_business_day_window(db_session):
    account_a = _make_account(db_session, "テスト手動振替口座E")
    account_b = _make_account(db_session, "テスト手動振替口座F")
    day1 = datetime.date(2026, 7, 6)
    day2 = datetime.date(2026, 7, 13)
    txn_out = _make_transaction(db_session, account_a.id, day1, decimal.Decimal("-8000"), "出金", "gap-out")
    txn_in = _make_transaction(db_session, account_b.id, day2, decimal.Decimal("8000"), "入金", "gap-in")

    with pytest.raises(transfer_management.TransferLinkError):
        transfer_management.create_manual_transfer_link(db_session, txn_out.id, txn_in.id)


def test_create_manual_transfer_link_rejects_already_linked_transaction(db_session):
    account_a = _make_account(db_session, "テスト手動振替口座G")
    account_b = _make_account(db_session, "テスト手動振替口座H")
    account_c = _make_account(db_session, "テスト手動振替口座I")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-8000"), "出金", "dup-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("8000"), "入金", "dup-in")
    other_txn = _make_transaction(db_session, account_c.id, day, decimal.Decimal("8000"), "別入金", "dup-other")
    db_session.add(Transfer(from_transaction_id=txn_out.id, to_transaction_id=txn_in.id, match_confidence="manual"))
    db_session.flush()

    with pytest.raises(transfer_management.TransferLinkError):
        transfer_management.create_manual_transfer_link(db_session, txn_out.id, other_txn.id)


def test_delete_transfer_link_removes_row(db_session):
    account_a = _make_account(db_session, "テスト振替解除口座A")
    account_b = _make_account(db_session, "テスト振替解除口座B")
    day = datetime.date(2026, 6, 1)
    txn_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-8000"), "出金", "del-out")
    txn_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("8000"), "入金", "del-in")
    transfer = Transfer(from_transaction_id=txn_out.id, to_transaction_id=txn_in.id, match_confidence="manual")
    db_session.add(transfer)
    db_session.flush()
    transfer_id = transfer.id

    deleted = transfer_management.delete_transfer_link(db_session, transfer_id)

    assert deleted is True
    assert db_session.get(Transfer, transfer_id) is None


def test_delete_transfer_link_returns_false_when_not_found(db_session):
    assert transfer_management.delete_transfer_link(db_session, 999999999) is False


def test_list_unlinked_candidates_excludes_already_linked(db_session):
    account_a = _make_account(db_session, "テスト候補口座A")
    account_b = _make_account(db_session, "テスト候補口座B")
    day = datetime.date(2026, 6, 1)
    linked_out = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-1000"), "リンク済み出金", "cand-linked-out")
    linked_in = _make_transaction(db_session, account_b.id, day, decimal.Decimal("1000"), "リンク済み入金", "cand-linked-in")
    unlinked = _make_transaction(db_session, account_a.id, day, decimal.Decimal("-2000"), "未リンク", "cand-unlinked")
    db_session.add(Transfer(from_transaction_id=linked_out.id, to_transaction_id=linked_in.id, match_confidence="auto"))
    db_session.flush()

    candidates = transfer_management.list_unlinked_candidates(db_session, as_of=day)
    candidate_ids = {txn.id for txn in candidates}

    assert unlinked.id in candidate_ids
    assert linked_out.id not in candidate_ids
    assert linked_in.id not in candidate_ids
