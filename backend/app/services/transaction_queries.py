import datetime
import decimal
import uuid

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import Account, Category, Transaction, Transfer
from app.services.categorization import categorize_with_rules, load_category_rules
from app.services.dedup import compute_source_hash

_DEFAULT_PAGE_SIZE = 50


class TransactionValidationError(ValueError):
    """取引作成・更新時のバリデーションエラー。"""


def _transfer_exists_expr():
    return exists().where(
        or_(Transfer.from_transaction_id == Transaction.id, Transfer.to_transaction_id == Transaction.id)
    )


def list_transactions(
    session: Session,
    *,
    account_id: int | None = None,
    category_id: int | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    uncategorized_only: bool = False,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> tuple[list[tuple[Transaction, bool]], int]:
    """フィルタ条件に合致する取引を新しい日付順にページングして返す(振替有無フラグ・総件数付き)。"""
    filters = []
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if category_id is not None:
        filters.append(Transaction.category_id == category_id)
    if date_from is not None:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to is not None:
        filters.append(Transaction.transaction_date <= date_to)
    if uncategorized_only:
        filters.append(Transaction.category_id.is_(None))

    total = session.execute(select(func.count()).select_from(Transaction).where(*filters)).scalar_one()

    stmt = (
        select(Transaction, _transfer_exists_expr())
        .where(*filters)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = [(txn, is_transferred) for txn, is_transferred in session.execute(stmt).all()]
    return rows, total


def is_transaction_transferred(session: Session, transaction_id: int) -> bool:
    return session.execute(select(_transfer_exists_expr()).where(Transaction.id == transaction_id)).scalar_one()


def update_transaction(session: Session, transaction_id: int, updates: dict) -> Transaction | None:
    """category_id・business_ratioを部分更新する(updatesに含まれないフィールドは変更しない)。"""
    txn = session.get(Transaction, transaction_id)
    if txn is None:
        return None

    new_category_id = updates.get("category_id")
    if "category_id" in updates and new_category_id is not None:
        if session.get(Category, new_category_id) is None:
            raise TransactionValidationError("指定されたカテゴリが見つかりません")

    for field, value in updates.items():
        setattr(txn, field, value)
    session.flush()
    return txn


def create_manual_transaction(
    session: Session,
    *,
    account_id: int | None,
    transaction_date: datetime.date,
    amount: decimal.Decimal,
    description: str,
    category_id: int | None,
    business_ratio: decimal.Decimal,
) -> Transaction:
    """現金払い等、自動取込元のない取引を手動で新規登録する(source_type=manual)。"""
    if amount == 0:
        raise TransactionValidationError("金額には0以外の値を指定してください")
    if account_id is not None and session.get(Account, account_id) is None:
        raise TransactionValidationError("指定された口座が見つかりません")
    if category_id is not None and session.get(Category, category_id) is None:
        raise TransactionValidationError("指定されたカテゴリが見つかりません")

    source_unique_id = f"manual-{uuid.uuid4()}"
    txn = Transaction(
        account_id=account_id,
        transaction_date=transaction_date,
        amount=amount,
        description=description,
        category_id=category_id,
        business_ratio=business_ratio,
        source_type="manual",
        source_hash=compute_source_hash(account_id, transaction_date, amount, description, source_unique_id),
        raw_data={"manual_entry": True},
    )
    session.add(txn)
    session.flush()
    return txn


def recategorize_uncategorized(session: Session) -> int:
    """category_idがNULLの取引にのみm_category_rulesを再適用する(手動分類済みは上書きしない)。"""
    rules = load_category_rules(session)
    uncategorized = session.execute(select(Transaction).where(Transaction.category_id.is_(None))).scalars().all()

    updated_count = 0
    for txn in uncategorized:
        category_id = categorize_with_rules(rules, txn.description)
        if category_id is not None:
            txn.category_id = category_id
            updated_count += 1
    return updated_count
