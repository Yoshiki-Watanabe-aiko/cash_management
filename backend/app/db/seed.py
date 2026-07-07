"""初期マスタデータ投入スクリプト（冪等）。

実行方法: uv run python -m app.db.seed
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.models import AssetClass, Category, Institution

INSTITUTIONS: list[tuple[str, str]] = [
    # クレジットカード
    ("三井住友カード", "credit_card"),
    ("楽天カード", "credit_card"),
    ("EPOSカード", "credit_card"),
    ("PayPayカード", "credit_card"),
    ("viewカード", "credit_card"),
    ("セゾンカード", "credit_card"),
    ("イオンカード", "credit_card"),
    # 銀行
    ("楽天銀行", "bank"),
    ("三井住友銀行", "bank"),
    ("三菱UFJ銀行", "bank"),
    ("ゆうちょ銀行", "bank"),
    ("PayPay銀行", "bank"),
    ("イオン銀行", "bank"),
    ("住信SBIネット銀行", "bank"),
    ("みずほ銀行", "bank"),
    ("りそな銀行", "bank"),
    # 証券会社
    ("楽天証券", "securities"),
    ("SBI証券", "securities"),
    ("三菱UFJeスマート証券", "securities"),
    ("マネックス証券", "securities"),
    # QRコード決済
    ("PayPay", "qr_payment"),
    ("楽天Pay", "qr_payment"),
]

ASSET_CLASSES: list[str] = ["現金", "国内株式", "投資信託", "ローン"]

CATEGORIES: list[str] = [
    "食費",
    "日用品費",
    "交通費",
    "通信費",
    "水道光熱費",
    "住居費",
    "医療費",
    "保険料",
    "教育費",
    "娯楽・レジャー費",
    "被服・美容費",
    "税金・社会保険料",
    "消耗品費",
    "接待交際費",
    "地代家賃",
    "外注費",
    "広告宣伝費",
    "給与収入",
    "事業収入",
    "投資収益",
    "その他",
]


def seed_institutions(db) -> int:
    existing = {name for (name,) in db.execute(select(Institution.institution_name))}
    to_add = [
        Institution(institution_name=name, institution_type=itype)
        for name, itype in INSTITUTIONS
        if name not in existing
    ]
    db.add_all(to_add)
    return len(to_add)


def seed_asset_classes(db) -> None:
    stmt = pg_insert(AssetClass).values(
        [{"asset_class_name": name} for name in ASSET_CLASSES]
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["asset_class_name"])
    db.execute(stmt)


def seed_categories(db) -> None:
    stmt = pg_insert(Category).values([{"category_name": name} for name in CATEGORIES])
    stmt = stmt.on_conflict_do_nothing(index_elements=["category_name"])
    db.execute(stmt)


def main() -> None:
    with SessionLocal() as db:
        added_institutions = seed_institutions(db)
        seed_asset_classes(db)
        seed_categories(db)
        db.commit()

        institution_count = db.scalar(select(func.count()).select_from(Institution))
        asset_class_count = db.scalar(select(func.count()).select_from(AssetClass))
        category_count = db.scalar(select(func.count()).select_from(Category))
        print(
            f"institutions: +{added_institutions} (total {institution_count}), "
            f"asset_classes (total {asset_class_count}), "
            f"categories (total {category_count})"
        )


if __name__ == "__main__":
    main()
