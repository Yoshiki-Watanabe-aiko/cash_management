import datetime

from sqlalchemy import select

from app.models import Account, Institution, Transaction, Transfer
from app.services.transfer_detection import detect_and_link_transfers


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _make_account(session, name: str, institution_id: int) -> Account:
    account = Account(
        institution_id=institution_id,
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
        business_ratio=0,
        source_type="moneyforward_csv",
        source_hash=f"test-hash-{hash_suffix}",
    )
    session.add(txn)
    session.flush()
    return txn


def test_links_matching_transfer_pair(db_session):
    institution_id = _bank_institution_id(db_session)
    account_a = _make_account(db_session, "テスト振替元口座", institution_id)
    account_b = _make_account(db_session, "テスト振替先口座", institution_id)

    day = datetime.date(2026, 7, 8)
    txn_out = _make_transaction(db_session, account_a.id, day, -10000, "テスト振替先口座への振替", "out1")
    txn_in = _make_transaction(db_session, account_b.id, day, 10000, "振込", "in1")

    linked_count = detect_and_link_transfers(db_session, as_of=day)
    db_session.flush()

    assert linked_count == 1
    transfer = db_session.execute(select(Transfer)).scalar_one()
    assert transfer.from_transaction_id == txn_out.id
    assert transfer.to_transaction_id == txn_in.id


def test_does_not_link_when_amount_differs(db_session):
    institution_id = _bank_institution_id(db_session)
    account_a = _make_account(db_session, "テスト振替元口座2", institution_id)
    account_b = _make_account(db_session, "テスト振替先口座2", institution_id)

    day = datetime.date(2026, 7, 8)
    _make_transaction(db_session, account_a.id, day, -10000, "テスト振替先口座2への振替", "out2")
    _make_transaction(db_session, account_b.id, day, 9000, "振込", "in2")

    linked_count = detect_and_link_transfers(db_session, as_of=day)

    assert linked_count == 0


def test_does_not_link_when_description_lacks_name_match(db_session):
    institution_id = _bank_institution_id(db_session)
    account_a = _make_account(db_session, "テスト振替元口座3", institution_id)
    account_b = _make_account(db_session, "テスト振替先口座3", institution_id)

    day = datetime.date(2026, 7, 8)
    _make_transaction(db_session, account_a.id, day, -10000, "コンビニ", "out3")
    _make_transaction(db_session, account_b.id, day, 10000, "入金", "in3")

    linked_count = detect_and_link_transfers(db_session, as_of=day)

    assert linked_count == 0


def test_does_not_relink_already_linked_transactions(db_session):
    institution_id = _bank_institution_id(db_session)
    account_a = _make_account(db_session, "テスト振替元口座4", institution_id)
    account_b = _make_account(db_session, "テスト振替先口座4", institution_id)

    day = datetime.date(2026, 7, 8)
    _make_transaction(db_session, account_a.id, day, -10000, "テスト振替先口座4への振替", "out4")
    _make_transaction(db_session, account_b.id, day, 10000, "振込", "in4")

    first_run = detect_and_link_transfers(db_session, as_of=day)
    db_session.flush()
    second_run = detect_and_link_transfers(db_session, as_of=day)

    assert first_run == 1
    assert second_run == 0


def test_does_not_link_beyond_business_day_window(db_session):
    institution_id = _bank_institution_id(db_session)
    account_a = _make_account(db_session, "テスト振替元口座5", institution_id)
    account_b = _make_account(db_session, "テスト振替先口座5", institution_id)

    # 2026-07-06(月)と2026-07-13(月)は間に5営業日あり、0〜3営業日以内の条件を満たさない
    day1 = datetime.date(2026, 7, 6)
    day2 = datetime.date(2026, 7, 13)
    _make_transaction(db_session, account_a.id, day1, -10000, "テスト振替先口座5への振替", "out5")
    _make_transaction(db_session, account_b.id, day2, 10000, "振込", "in5")

    linked_count = detect_and_link_transfers(db_session, as_of=day2)

    assert linked_count == 0
