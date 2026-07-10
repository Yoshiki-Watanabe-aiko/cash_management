import datetime
import decimal

import pytest
from sqlalchemy import select

from app.models import Account, Category, CategoryRule, Institution, Transaction, Transfer
from app.services import transaction_queries


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


def _make_transaction(
    session,
    account_id: int,
    d: datetime.date,
    amount,
    description: str,
    hash_suffix: str,
    *,
    category_id: int | None = None,
) -> Transaction:
    txn = Transaction(
        account_id=account_id,
        transaction_date=d,
        amount=amount,
        description=description,
        category_id=category_id,
        business_ratio=decimal.Decimal("0"),
        source_type="moneyforward_csv",
        source_hash=f"txn-query-test-{hash_suffix}",
    )
    session.add(txn)
    session.flush()
    return txn


def test_list_transactions_filters_by_account_and_paginates(db_session):
    account_a = _make_account(db_session, "テスト一覧口座A")
    account_b = _make_account(db_session, "テスト一覧口座B")

    for i in range(3):
        _make_transaction(db_session, account_a.id, datetime.date(2026, 6, i + 1), -100, f"取引A{i}", f"list-a{i}")
    _make_transaction(db_session, account_b.id, datetime.date(2026, 6, 1), -100, "取引B", "list-b")

    rows, total = transaction_queries.list_transactions(db_session, account_id=account_a.id, page=1, page_size=2)

    assert total == 3
    assert len(rows) == 2
    assert all(txn.account_id == account_a.id for txn, _ in rows)


def test_list_transactions_filters_by_category_and_date_range(db_session):
    account = _make_account(db_session, "テストフィルタ口座")
    category = Category(category_name="テストフィルタカテゴリ")
    db_session.add(category)
    db_session.flush()

    in_range_matching = _make_transaction(
        db_session, account.id, datetime.date(2026, 6, 15), -100, "対象内", "filter-match", category_id=category.id
    )
    _make_transaction(
        db_session, account.id, datetime.date(2026, 6, 15), -100, "カテゴリ違い", "filter-other-category"
    )
    _make_transaction(
        db_session, account.id, datetime.date(2026, 5, 1), -100, "期間外(前)", "filter-before", category_id=category.id
    )
    _make_transaction(
        db_session, account.id, datetime.date(2026, 7, 1), -100, "期間外(後)", "filter-after", category_id=category.id
    )

    rows, total = transaction_queries.list_transactions(
        db_session,
        account_id=account.id,
        category_id=category.id,
        date_from=datetime.date(2026, 6, 1),
        date_to=datetime.date(2026, 6, 30),
    )

    assert total == 1
    assert rows[0][0].id == in_range_matching.id


def test_list_transactions_marks_transferred_flag(db_session):
    account = _make_account(db_session, "テスト振替フラグ口座")
    txn_out = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), -5000, "振替出金", "flag-out")
    txn_in = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), 5000, "振替入金", "flag-in")
    db_session.add(Transfer(from_transaction_id=txn_out.id, to_transaction_id=txn_in.id, match_confidence="auto"))
    db_session.flush()

    rows, _ = transaction_queries.list_transactions(db_session, account_id=account.id)

    flags = {txn.id: is_transferred for txn, is_transferred in rows}
    assert flags[txn_out.id] is True
    assert flags[txn_in.id] is True


def test_list_transactions_uncategorized_only_filter(db_session):
    account = _make_account(db_session, "テスト未分類フィルタ口座")
    category = Category(category_name="テスト分類済みカテゴリ")
    db_session.add(category)
    db_session.flush()

    _make_transaction(
        db_session, account.id, datetime.date(2026, 6, 1), -100, "分類済み", "uncat-a", category_id=category.id
    )
    _make_transaction(db_session, account.id, datetime.date(2026, 6, 2), -100, "未分類", "uncat-b")

    rows, total = transaction_queries.list_transactions(db_session, account_id=account.id, uncategorized_only=True)

    assert total == 1
    assert rows[0][0].description == "未分類"


def test_update_transaction_changes_only_provided_fields(db_session):
    account = _make_account(db_session, "テスト更新口座")
    txn = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), -100, "更新対象", "update-1")

    updated = transaction_queries.update_transaction(
        db_session, txn.id, {"business_ratio": decimal.Decimal("30")}
    )

    assert updated is not None
    assert updated.business_ratio == decimal.Decimal("30")
    assert updated.category_id is None


def test_update_transaction_returns_none_when_not_found(db_session):
    assert transaction_queries.update_transaction(db_session, 999999999, {"business_ratio": decimal.Decimal("0")}) is None


def test_update_transaction_rejects_unknown_category_id(db_session):
    account = _make_account(db_session, "テスト不正カテゴリ口座")
    txn = _make_transaction(db_session, account.id, datetime.date(2026, 6, 1), -100, "対象", "update-bad-category")

    with pytest.raises(transaction_queries.TransactionValidationError):
        transaction_queries.update_transaction(db_session, txn.id, {"category_id": 999999999})


def test_recategorize_uncategorized_applies_rules_and_skips_already_categorized(db_session):
    account = _make_account(db_session, "テスト再分類口座")
    rule_category = Category(category_name="テスト再分類カテゴリ")
    already_category = Category(category_name="テスト既存カテゴリ")
    db_session.add_all([rule_category, already_category])
    db_session.flush()
    db_session.add(CategoryRule(keyword_pattern="スーパー", category_id=rule_category.id, priority=100))
    db_session.flush()

    uncategorized_matching = _make_transaction(
        db_session, account.id, datetime.date(2026, 6, 1), -100, "スーパーで買い物", "recat-a"
    )
    uncategorized_no_match = _make_transaction(
        db_session, account.id, datetime.date(2026, 6, 2), -100, "該当なし", "recat-b"
    )
    already_categorized = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 3),
        -100,
        "スーパーで買い物だが既に分類済み",
        "recat-c",
        category_id=already_category.id,
    )
    db_session.flush()

    updated_count = transaction_queries.recategorize_uncategorized(db_session)

    assert updated_count == 1
    assert uncategorized_matching.category_id == rule_category.id
    assert uncategorized_no_match.category_id is None
    assert already_categorized.category_id == already_category.id


def test_create_manual_transaction_with_account(db_session):
    account = _make_account(db_session, "テスト手動登録口座")
    category = Category(category_name="テスト手動登録カテゴリ")
    db_session.add(category)
    db_session.flush()

    txn = transaction_queries.create_manual_transaction(
        db_session,
        account_id=account.id,
        transaction_date=datetime.date(2026, 7, 1),
        amount=decimal.Decimal("-500"),
        description="現金払い(手動登録)",
        category_id=category.id,
        business_ratio=decimal.Decimal("0"),
    )

    assert txn.id is not None
    assert txn.source_type == "manual"
    assert txn.account_id == account.id
    assert txn.raw_data == {"manual_entry": True}


def test_create_manual_transaction_without_account_for_cash_payment(db_session):
    txn = transaction_queries.create_manual_transaction(
        db_session,
        account_id=None,
        transaction_date=datetime.date(2026, 7, 1),
        amount=decimal.Decimal("-1000"),
        description="現金(財布)払い",
        category_id=None,
        business_ratio=decimal.Decimal("0"),
    )

    assert txn.id is not None
    assert txn.account_id is None


def test_create_manual_transaction_allows_duplicate_looking_entries(db_session):
    """同一日・同一金額・同一摘要でも手動登録は都度別取引として作成できる(source_hashが衝突しない)。"""
    kwargs = dict(
        account_id=None,
        transaction_date=datetime.date(2026, 7, 1),
        amount=decimal.Decimal("-500"),
        description="コンビニ",
        category_id=None,
        business_ratio=decimal.Decimal("0"),
    )

    first = transaction_queries.create_manual_transaction(db_session, **kwargs)
    second = transaction_queries.create_manual_transaction(db_session, **kwargs)

    assert first.id != second.id
    assert first.source_hash != second.source_hash


def test_create_manual_transaction_rejects_zero_amount(db_session):
    with pytest.raises(transaction_queries.TransactionValidationError):
        transaction_queries.create_manual_transaction(
            db_session,
            account_id=None,
            transaction_date=datetime.date(2026, 7, 1),
            amount=decimal.Decimal("0"),
            description="金額ゼロ",
            category_id=None,
            business_ratio=decimal.Decimal("0"),
        )


def test_create_manual_transaction_rejects_unknown_account_id(db_session):
    with pytest.raises(transaction_queries.TransactionValidationError):
        transaction_queries.create_manual_transaction(
            db_session,
            account_id=999999999,
            transaction_date=datetime.date(2026, 7, 1),
            amount=decimal.Decimal("-100"),
            description="不正口座",
            category_id=None,
            business_ratio=decimal.Decimal("0"),
        )


def test_create_manual_transaction_rejects_unknown_category_id(db_session):
    with pytest.raises(transaction_queries.TransactionValidationError):
        transaction_queries.create_manual_transaction(
            db_session,
            account_id=None,
            transaction_date=datetime.date(2026, 7, 1),
            amount=decimal.Decimal("-100"),
            description="不正カテゴリ",
            category_id=999999999,
            business_ratio=decimal.Decimal("0"),
        )
