import datetime
import decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Account, AssetClass, AssetSnapshot, Transaction

_FUND_KEYWORDS: tuple[str, ...] = ("ファンド", "インデックス", "REIT", "リート", "トラスト", "オープン")


def _asset_class_id(session: Session, asset_class_name: str) -> int:
    return session.execute(
        select(AssetClass.id).where(AssetClass.asset_class_name == asset_class_name)
    ).scalar_one()


def _upsert_snapshot(
    session: Session,
    snapshot_date: datetime.date,
    account_id: int,
    asset_class_id: int,
    ticker_or_name: str,
    current_value: decimal.Decimal,
    book_value: decimal.Decimal | None,
    source_type: str,
) -> None:
    stmt = pg_insert(AssetSnapshot).values(
        snapshot_date=snapshot_date,
        account_id=account_id,
        asset_class_id=asset_class_id,
        ticker_or_name=ticker_or_name,
        current_value=current_value,
        book_value=book_value,
        source_type=source_type,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["snapshot_date", "account_id", "ticker_or_name"],
        set_={
            "asset_class_id": stmt.excluded.asset_class_id,
            "current_value": stmt.excluded.current_value,
            "book_value": stmt.excluded.book_value,
            "source_type": stmt.excluded.source_type,
        },
    )
    session.execute(stmt)


def compute_cumulative_balance(session: Session, account: Account, as_of: datetime.date) -> decimal.Decimal:
    """初期残高+取引累積(as_of以前)で残高を算出する(5.5章)。"""
    transaction_total = session.execute(
        select(Transaction.amount)
        .where(Transaction.account_id == account.id)
        .where(Transaction.transaction_date <= as_of)
    ).scalars().all()
    return (account.opening_balance or decimal.Decimal("0")) + sum(
        transaction_total, decimal.Decimal("0")
    )


def write_cumulative_snapshot(session: Session, account: Account, as_of: datetime.date) -> None:
    """累積方式口座(銀行・チャージ式QR決済)の日次残高スナップショットを書き込む。"""
    current_value = compute_cumulative_balance(session, account, as_of)
    _upsert_snapshot(
        session,
        snapshot_date=as_of,
        account_id=account.id,
        asset_class_id=_asset_class_id(session, "現金"),
        ticker_or_name=account.account_name,
        current_value=current_value,
        book_value=None,
        source_type="cumulative",
    )


def _classify_security_asset_class(ticker_or_name: str) -> str:
    if any(keyword in ticker_or_name for keyword in _FUND_KEYWORDS):
        return "投資信託"
    return "国内株式"


def write_moneyforward_loan_snapshot(
    session: Session, account: Account, snapshot_date: datetime.date, outstanding_balance: decimal.Decimal
) -> None:
    """MF連携によるローン残高スナップショットを書き込む(マイナス値、ADR 0002)。"""
    _upsert_snapshot(
        session,
        snapshot_date=snapshot_date,
        account_id=account.id,
        asset_class_id=_asset_class_id(session, "ローン"),
        ticker_or_name=account.account_name,
        current_value=-abs(outstanding_balance),
        book_value=None,
        source_type="moneyforward",
    )


def write_moneyforward_securities_snapshot(
    session: Session,
    account: Account,
    snapshot_date: datetime.date,
    ticker_or_name: str,
    current_value: decimal.Decimal,
    book_value: decimal.Decimal | None,
) -> None:
    """MF連携による証券評価額スナップショットを書き込む。"""
    asset_class_name = _classify_security_asset_class(ticker_or_name)
    _upsert_snapshot(
        session,
        snapshot_date=snapshot_date,
        account_id=account.id,
        asset_class_id=_asset_class_id(session, asset_class_name),
        ticker_or_name=ticker_or_name,
        current_value=current_value,
        book_value=book_value,
        source_type="moneyforward",
    )
