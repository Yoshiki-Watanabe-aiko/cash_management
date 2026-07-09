import datetime
import decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, Institution

VALID_ACCOUNT_TYPES = {"bank", "credit_card", "securities", "qr_payment", "loan"}
VALID_BALANCE_METHODS = {"cumulative", "moneyforward", "manual"}
NOT_NULLABLE_UPDATE_FIELDS = {
    "institution_id",
    "account_name",
    "account_type",
    "is_business",
    "is_active",
    "default_business_ratio",
    "tracks_balance",
}


class AccountValidationError(ValueError):
    """口座作成・更新時のバリデーションエラー。"""


def _validate_business_rules(
    *,
    account_type: str,
    tracks_balance: bool,
    balance_method: str | None,
    opening_balance: decimal.Decimal | None,
    opening_balance_date: datetime.date | None,
) -> None:
    if account_type not in VALID_ACCOUNT_TYPES:
        raise AccountValidationError(f"account_typeは{sorted(VALID_ACCOUNT_TYPES)}のいずれかである必要があります")
    if tracks_balance:
        if balance_method not in VALID_BALANCE_METHODS:
            raise AccountValidationError(
                f"tracks_balance=trueの場合、balance_methodは{sorted(VALID_BALANCE_METHODS)}のいずれかが必要です"
            )
        if balance_method == "cumulative" and (opening_balance is None or opening_balance_date is None):
            raise AccountValidationError(
                "balance_method=cumulativeの場合、opening_balanceとopening_balance_dateが必須です"
            )
    elif balance_method is not None:
        raise AccountValidationError("tracks_balance=falseの口座にbalance_methodを設定できません")


def list_accounts_detail(session: Session) -> list[Account]:
    """全口座を詳細情報付きで返す(口座管理画面向け)。"""
    return session.execute(select(Account).order_by(Account.id)).scalars().all()


def create_account(session: Session, *, institution_id: int, **fields) -> Account:
    """口座を新規作成する(残高追跡設定の整合性を検証)。"""
    if session.get(Institution, institution_id) is None:
        raise AccountValidationError("指定された金融機関が見つかりません")

    _validate_business_rules(
        account_type=fields["account_type"],
        tracks_balance=fields["tracks_balance"],
        balance_method=fields.get("balance_method"),
        opening_balance=fields.get("opening_balance"),
        opening_balance_date=fields.get("opening_balance_date"),
    )

    account = Account(institution_id=institution_id, **fields)
    session.add(account)
    session.flush()
    return account


def update_account(session: Session, account_id: int, updates: dict) -> Account | None:
    """口座を部分更新する(残高追跡設定は更新後の状態全体で再検証)。"""
    account = session.get(Account, account_id)
    if account is None:
        return None

    for field in NOT_NULLABLE_UPDATE_FIELDS:
        if field in updates and updates[field] is None:
            raise AccountValidationError(f"{field}にnullを指定することはできません")

    if "institution_id" in updates and session.get(Institution, updates["institution_id"]) is None:
        raise AccountValidationError("指定された金融機関が見つかりません")

    merged = {
        "account_type": updates.get("account_type", account.account_type),
        "tracks_balance": updates.get("tracks_balance", account.tracks_balance),
        "balance_method": updates.get("balance_method", account.balance_method),
        "opening_balance": updates.get("opening_balance", account.opening_balance),
        "opening_balance_date": updates.get("opening_balance_date", account.opening_balance_date),
    }
    _validate_business_rules(**merged)

    for field, value in updates.items():
        setattr(account, field, value)

    if merged["balance_method"] != "cumulative":
        if "opening_balance" not in updates:
            account.opening_balance = None
        if "opening_balance_date" not in updates:
            account.opening_balance_date = None

    session.flush()
    return account
