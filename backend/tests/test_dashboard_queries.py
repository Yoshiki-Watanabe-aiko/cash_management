import datetime
import decimal

from sqlalchemy import select

from app.models import Account, AssetClass, AssetSnapshot, Budget, Category, Institution, Transaction, Transfer
from app.services import dashboard_queries


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def _asset_class_id(session, name: str) -> int:
    return session.execute(
        select(AssetClass.id).where(AssetClass.asset_class_name == name)
    ).scalar_one()


def _category_id(session, name: str) -> int:
    return session.execute(select(Category.id).where(Category.category_name == name)).scalar_one()


def _make_account(session, name: str, *, business_ratio=0) -> Account:
    account = Account(
        institution_id=_bank_institution_id(session),
        account_name=name,
        account_type="bank",
        default_business_ratio=business_ratio,
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
    business_ratio=decimal.Decimal("0"),
) -> Transaction:
    txn = Transaction(
        account_id=account_id,
        transaction_date=d,
        amount=amount,
        description=description,
        category_id=category_id,
        business_ratio=business_ratio,
        source_type="moneyforward_csv",
        source_hash=f"dash-test-{hash_suffix}",
    )
    session.add(txn)
    session.flush()
    return txn


def test_net_worth_history_sums_snapshots_by_date(db_session):
    account = _make_account(db_session, "テストNW口座")
    cash_class_id = _asset_class_id(db_session, "現金")
    loan_class_id = _asset_class_id(db_session, "ローン")

    day1 = datetime.date(2026, 6, 1)
    day2 = datetime.date(2026, 6, 2)
    db_session.add_all(
        [
            AssetSnapshot(
                snapshot_date=day1,
                account_id=account.id,
                asset_class_id=cash_class_id,
                ticker_or_name=account.account_name,
                current_value=decimal.Decimal("100000"),
                source_type="cumulative",
            ),
            AssetSnapshot(
                snapshot_date=day1,
                account_id=account.id,
                asset_class_id=loan_class_id,
                ticker_or_name="ローン口座",
                current_value=decimal.Decimal("-30000"),
                source_type="manual",
            ),
            AssetSnapshot(
                snapshot_date=day2,
                account_id=account.id,
                asset_class_id=cash_class_id,
                ticker_or_name=account.account_name,
                current_value=decimal.Decimal("110000"),
                source_type="cumulative",
            ),
        ]
    )
    db_session.flush()

    history = dashboard_queries.net_worth_history(db_session, months=12, as_of=day2)

    points = {point.snapshot_date: point.net_worth for point in history}
    assert points[day1] == decimal.Decimal("70000")
    assert points[day2] == decimal.Decimal("110000")


def test_net_worth_history_excludes_snapshots_before_window(db_session):
    account = _make_account(db_session, "テストNW口座2")
    cash_class_id = _asset_class_id(db_session, "現金")

    old_day = datetime.date(2020, 1, 1)
    recent_day = datetime.date(2026, 6, 1)
    db_session.add_all(
        [
            AssetSnapshot(
                snapshot_date=old_day,
                account_id=account.id,
                asset_class_id=cash_class_id,
                ticker_or_name=account.account_name,
                current_value=decimal.Decimal("1"),
                source_type="cumulative",
            ),
            AssetSnapshot(
                snapshot_date=recent_day,
                account_id=account.id,
                asset_class_id=cash_class_id,
                ticker_or_name=account.account_name,
                current_value=decimal.Decimal("2"),
                source_type="cumulative",
            ),
        ]
    )
    db_session.flush()

    history = dashboard_queries.net_worth_history(db_session, months=1, as_of=recent_day)

    dates = {point.snapshot_date for point in history}
    assert old_day not in dates
    assert recent_day in dates


def test_budget_progress_computes_business_ratio_apportioned_spend(db_session):
    account = _make_account(db_session, "テスト予算口座", business_ratio=50)
    category_id = _category_id(db_session, "接待交際費")
    year_month = "2026-06"
    db_session.add(
        Budget(category_id=category_id, year_month=year_month, is_business=True, budget_amount=decimal.Decimal("50000"))
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 10),
        decimal.Decimal("-10000"),
        "接待",
        "budget1",
        category_id=category_id,
        business_ratio=decimal.Decimal("50"),
    )
    db_session.flush()

    results = dashboard_queries.budget_progress(db_session, year_month=year_month)

    matching = [r for r in results if r.category_id == category_id]
    assert len(matching) == 1
    assert matching[0].spent_amount == decimal.Decimal("5000")
    assert matching[0].progress_ratio == decimal.Decimal("0.1")


def test_budget_progress_does_not_mix_amounts_across_categories(db_session):
    account = _make_account(db_session, "テスト複数予算口座", business_ratio=100)
    year_month = "2026-06"
    category_a_id = _category_id(db_session, "広告宣伝費")
    category_b_id = _category_id(db_session, "消耗品費")
    db_session.add_all(
        [
            Budget(category_id=category_a_id, year_month=year_month, is_business=True, budget_amount=decimal.Decimal("10000")),
            Budget(category_id=category_b_id, year_month=year_month, is_business=True, budget_amount=decimal.Decimal("20000")),
        ]
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 10),
        decimal.Decimal("-3000"),
        "広告費",
        "multi-budget-a",
        category_id=category_a_id,
        business_ratio=decimal.Decimal("100"),
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 11),
        decimal.Decimal("-7000"),
        "消耗品",
        "multi-budget-b",
        category_id=category_b_id,
        business_ratio=decimal.Decimal("100"),
    )
    db_session.flush()

    results = dashboard_queries.budget_progress(db_session, year_month=year_month)
    by_category = {r.category_id: r.spent_amount for r in results}

    assert by_category[category_a_id] == decimal.Decimal("3000")
    assert by_category[category_b_id] == decimal.Decimal("7000")


def test_budget_progress_excludes_transferred_transactions(db_session):
    account = _make_account(db_session, "テスト予算除外口座", business_ratio=100)
    category_id = _category_id(db_session, "外注費")
    year_month = "2026-06"
    db_session.add(
        Budget(category_id=category_id, year_month=year_month, is_business=True, budget_amount=decimal.Decimal("10000"))
    )
    txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 15),
        decimal.Decimal("-5000"),
        "振替扱い",
        "budget2",
        category_id=category_id,
        business_ratio=decimal.Decimal("100"),
    )
    other_txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 15),
        decimal.Decimal("5000"),
        "相手側",
        "budget2b",
    )
    db_session.add(Transfer(from_transaction_id=txn.id, to_transaction_id=other_txn.id, match_confidence="manual"))
    db_session.flush()

    results = dashboard_queries.budget_progress(db_session, year_month=year_month)

    matching = [r for r in results if r.category_id == category_id]
    assert matching[0].spent_amount == decimal.Decimal("0")


def test_personal_cashflow_apportions_personal_ratio_and_excludes_transfers(db_session):
    account = _make_account(db_session, "テストCF口座")
    year_month = "2026-06"

    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 5),
        decimal.Decimal("100000"),
        "給与",
        "cf-income",
        business_ratio=decimal.Decimal("0"),
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 6),
        decimal.Decimal("-10000"),
        "食料品",
        "cf-expense",
        business_ratio=decimal.Decimal("20"),
    )
    txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 7),
        decimal.Decimal("-20000"),
        "振替出金",
        "cf-transfer-out",
        business_ratio=decimal.Decimal("0"),
    )
    other_txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 7),
        decimal.Decimal("20000"),
        "振替入金",
        "cf-transfer-in",
        business_ratio=decimal.Decimal("0"),
    )
    db_session.add(Transfer(from_transaction_id=txn.id, to_transaction_id=other_txn.id, match_confidence="auto"))
    db_session.flush()

    summary = dashboard_queries.personal_cashflow(db_session, year_month=year_month)

    assert summary.income == decimal.Decimal("100000")
    assert summary.expense == decimal.Decimal("8000")


def test_category_breakdown_sums_expenses_and_excludes_transfers(db_session):
    account = _make_account(db_session, "テストカテゴリ内訳口座")
    year_month = "2026-06"
    food_category_id = _category_id(db_session, "食費")

    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 1),
        decimal.Decimal("-3000"),
        "スーパー",
        "cat1",
        category_id=food_category_id,
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 2),
        decimal.Decimal("-2000"),
        "コンビニ",
        "cat2",
        category_id=food_category_id,
    )
    _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 3),
        decimal.Decimal("-1000"),
        "未分類の支出",
        "cat3",
        category_id=None,
    )
    txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 4),
        decimal.Decimal("-9000"),
        "振替",
        "cat4",
        category_id=food_category_id,
    )
    other_txn = _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 6, 4),
        decimal.Decimal("9000"),
        "振替入金",
        "cat4b",
    )
    db_session.add(Transfer(from_transaction_id=txn.id, to_transaction_id=other_txn.id, match_confidence="auto"))
    db_session.flush()

    results = dashboard_queries.category_breakdown(db_session, year_month=year_month)

    by_category = {item.category_name: item.amount for item in results}
    assert by_category["食費"] == decimal.Decimal("5000")
    assert by_category["未分類"] == decimal.Decimal("1000")
    assert results[0].category_name == "食費"
