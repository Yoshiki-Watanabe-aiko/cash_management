from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Institution

_WHITESPACE_CHARS = str.maketrans("", "", " 　")


def _normalize_label(label: str) -> str:
    return label.translate(_WHITESPACE_CHARS)


def resolve_account(session: Session, label: str) -> Account | None:
    """マネーフォワードME CSVの口座表示名からm_accountsを解決する(moneyforward_account_name優先、次点でaccount_name)。"""
    normalized = _normalize_label(label)
    accounts = session.execute(select(Account).where(Account.is_active.is_(True))).scalars().all()

    for account in accounts:
        if account.moneyforward_account_name and _normalize_label(account.moneyforward_account_name) == normalized:
            return account

    for account in accounts:
        if _normalize_label(account.account_name) == normalized:
            return account

    return None


def resolve_institution_by_sender(session: Session, from_address: str) -> Institution | None:
    """送信元メールアドレス(Fromヘッダ)からカード会社を解決する(ADR 0006/0010)。"""
    normalized = from_address.strip().lower()
    if not normalized:
        return None

    return session.execute(
        select(Institution).where(
            Institution.institution_type == "credit_card",
            func.lower(Institution.card_alert_sender_email) == normalized,
        )
    ).scalars().first()


def resolve_card_account(session: Session, institution_id: int, is_business: bool) -> Account | None:
    """カード会社IDと受信メールボックス(個人用/事業用)からm_accountsを解決する(ADR 0006)。"""
    return session.execute(
        select(Account).where(
            Account.institution_id == institution_id,
            Account.account_type == "credit_card",
            Account.is_business.is_(is_business),
            Account.is_active.is_(True),
        )
    ).scalars().first()
