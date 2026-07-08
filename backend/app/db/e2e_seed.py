"""Playwright E2Eテスト用の使い捨てデータベース初期化・シードスクリプト。

実行方法: uv run python -m app.db.e2e_seed
Playwrightのglobal setupから呼び出される想定(frontend/e2e/global-setup.ts参照)。

安全装置: DATABASE_URLのデータベース名に"test"を含まない場合は実行を拒否する。
本スクリプトはpublicスキーマを丸ごと破棄・再作成するため、誤って本番用の
cash_managementデータベース(ユーザー本人の実際の資産・取引データ)に対して
実行してしまう事故を防ぐ。
"""

import datetime
import hashlib
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.db.seed import seed_asset_classes, seed_categories, seed_institutions
from app.models import Account, AssetClass, AssetSnapshot, Budget, Category, CategoryRule, Institution, Transaction


def _source_hash(label: str) -> str:
    return hashlib.sha256(f"e2e-seed-{label}".encode("utf-8")).hexdigest()


def _reset_schema(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)


def _seed_fixtures(db: Session) -> None:
    seed_institutions(db)
    seed_asset_classes(db)
    seed_categories(db)
    db.flush()

    bank_a = db.execute(select(Institution).where(Institution.institution_name == "楽天銀行")).scalar_one()
    bank_b = db.execute(select(Institution).where(Institution.institution_name == "三井住友銀行")).scalar_one()
    card = db.execute(select(Institution).where(Institution.institution_name == "楽天カード")).scalar_one()
    cash_class = db.execute(select(AssetClass).where(AssetClass.asset_class_name == "現金")).scalar_one()

    today = datetime.date.today()
    opening_date = today - datetime.timedelta(days=90)

    account_rakuten = Account(
        institution_id=bank_a.id,
        account_name="楽天銀行 個人[E2E]",
        account_type="bank",
        is_business=False,
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=500000,
        opening_balance_date=opening_date,
    )
    account_smbc = Account(
        institution_id=bank_b.id,
        account_name="三井住友銀行 個人[E2E]",
        account_type="bank",
        is_business=False,
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
        opening_balance=200000,
        opening_balance_date=opening_date,
    )
    account_card = Account(
        institution_id=card.id,
        account_name="楽天カード 事業[E2E]",
        account_type="credit_card",
        is_business=True,
        default_business_ratio=100,
        tracks_balance=False,
    )
    db.add_all([account_rakuten, account_smbc, account_card])
    db.flush()

    food_category = db.execute(select(Category).where(Category.category_name == "食費")).scalar_one()
    salary_category = db.execute(select(Category).where(Category.category_name == "給与収入")).scalar_one()
    entertainment_category = db.execute(
        select(Category).where(Category.category_name == "接待交際費")
    ).scalar_one()

    db.add(CategoryRule(keyword_pattern="スーパー", category_id=food_category.id, priority=10))

    db.add(
        Budget(
            category_id=entertainment_category.id,
            year_month=f"{today.year:04d}-{today.month:02d}",
            is_business=True,
            budget_amount=50000,
        )
    )

    transactions = [
        Transaction(
            account_id=account_card.id,
            transaction_date=today,
            amount=-30000,
            description="取引先接待",
            category_id=entertainment_category.id,
            business_ratio=100,
            source_type="manual",
            source_hash=_source_hash("business-expense"),
        ),
        Transaction(
            account_id=account_rakuten.id,
            transaction_date=today,
            amount=-8000,
            description="スーパーで食料品購入",
            category_id=None,
            business_ratio=0,
            source_type="manual",
            source_hash=_source_hash("uncategorized-food"),
        ),
        Transaction(
            account_id=account_rakuten.id,
            transaction_date=today - datetime.timedelta(days=1),
            amount=250000,
            description="給与振込",
            category_id=salary_category.id,
            business_ratio=0,
            source_type="manual",
            source_hash=_source_hash("salary-income"),
        ),
        # 振替の手動紐づけE2E用: 未紐づけの出金・入金ペア(金額完全一致・同日)
        Transaction(
            account_id=account_rakuten.id,
            transaction_date=today,
            amount=-50000,
            description="振替出金",
            category_id=None,
            business_ratio=0,
            source_type="manual",
            source_hash=_source_hash("transfer-out"),
        ),
        Transaction(
            account_id=account_smbc.id,
            transaction_date=today,
            amount=50000,
            description="振替入金",
            category_id=None,
            business_ratio=0,
            source_type="manual",
            source_hash=_source_hash("transfer-in"),
        ),
    ]
    db.add_all(transactions)

    for offset_days, rakuten_value, smbc_value in (
        (60, 480000, 200000),
        (30, 495000, 200000),
        (0, 512000, 250000),
    ):
        snapshot_date = today - datetime.timedelta(days=offset_days)
        db.add_all(
            [
                AssetSnapshot(
                    snapshot_date=snapshot_date,
                    account_id=account_rakuten.id,
                    asset_class_id=cash_class.id,
                    ticker_or_name=account_rakuten.account_name,
                    current_value=rakuten_value,
                    source_type="cumulative",
                ),
                AssetSnapshot(
                    snapshot_date=snapshot_date,
                    account_id=account_smbc.id,
                    asset_class_id=cash_class.id,
                    ticker_or_name=account_smbc.account_name,
                    current_value=smbc_value,
                    source_type="cumulative",
                ),
            ]
        )


def main() -> None:
    db_name = settings.database_url.rsplit("/", 1)[-1]
    if "test" not in db_name:
        print(
            f"安全のため中断しました: データベース名'{db_name}'に'test'が含まれていません。"
            "E2Eテスト専用データベース(例: cash_management_test)のDATABASE_URLで実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = create_engine(settings.database_url)
    _reset_schema(engine)

    with Session(engine) as db:
        _seed_fixtures(db)
        db.commit()

    print(f"E2Eテスト用データベース'{db_name}'の初期化・シード投入が完了しました。")


if __name__ == "__main__":
    main()
