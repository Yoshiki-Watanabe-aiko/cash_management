from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategoryRule


def load_category_rules(session: Session) -> list[tuple[str, int]]:
    """m_category_rulesをpriority昇順で取得する(バッチ処理で使い回すための事前取得用)。"""
    return session.execute(
        select(CategoryRule.keyword_pattern, CategoryRule.category_id).order_by(
            CategoryRule.priority.asc(), CategoryRule.id.asc()
        )
    ).all()


def categorize_with_rules(rules: list[tuple[str, int]], description: str) -> int | None:
    """事前取得済みルールに対して摘要をマッチングする(最初に一致したcategory_idを返す、未分類はNone)。"""
    for keyword_pattern, category_id in rules:
        if keyword_pattern in description:
            return category_id
    return None


def categorize(session: Session, description: str) -> int | None:
    """摘要に対してm_category_rulesをpriority昇順で評価し、最初に一致したcategory_idを返す(未分類はNone)。"""
    return categorize_with_rules(load_category_rules(session), description)
