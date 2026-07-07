from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategoryRule


def categorize(session: Session, description: str) -> int | None:
    """摘要に対してm_category_rulesをpriority昇順で評価し、最初に一致したcategory_idを返す(未分類はNone)。"""
    rules = session.execute(
        select(CategoryRule.keyword_pattern, CategoryRule.category_id).order_by(
            CategoryRule.priority.asc(), CategoryRule.id.asc()
        )
    ).all()
    for keyword_pattern, category_id in rules:
        if keyword_pattern in description:
            return category_id
    return None
