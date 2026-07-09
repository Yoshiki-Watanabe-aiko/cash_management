from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryRule


class CategoryRuleValidationError(ValueError):
    """カテゴリルール作成・更新時のバリデーションエラー。"""


NOT_NULLABLE_UPDATE_FIELDS = {"keyword_pattern", "category_id", "priority"}


def list_category_rules(session: Session) -> list[CategoryRule]:
    """優先度(priority)昇順でルール一覧を返す。"""
    stmt = select(CategoryRule).order_by(CategoryRule.priority, CategoryRule.id)
    return session.execute(stmt).scalars().all()


def create_category_rule(
    session: Session, *, keyword_pattern: str, category_id: int, priority: int
) -> CategoryRule:
    """カテゴリ自動分類ルールを新規作成する。"""
    if session.get(Category, category_id) is None:
        raise CategoryRuleValidationError("指定されたカテゴリが見つかりません")

    rule = CategoryRule(keyword_pattern=keyword_pattern, category_id=category_id, priority=priority)
    session.add(rule)
    session.flush()
    return rule


def update_category_rule(session: Session, rule_id: int, updates: dict) -> CategoryRule | None:
    """keyword_pattern・category_id・priorityを部分更新する。"""
    rule = session.get(CategoryRule, rule_id)
    if rule is None:
        return None

    for field in NOT_NULLABLE_UPDATE_FIELDS:
        if field in updates and updates[field] is None:
            raise CategoryRuleValidationError(f"{field}にnullを指定することはできません")

    if "category_id" in updates and session.get(Category, updates["category_id"]) is None:
        raise CategoryRuleValidationError("指定されたカテゴリが見つかりません")

    for field, value in updates.items():
        setattr(rule, field, value)
    session.flush()
    return rule


def delete_category_rule(session: Session, rule_id: int) -> bool:
    """カテゴリルールを削除する。"""
    rule = session.get(CategoryRule, rule_id)
    if rule is None:
        return False
    session.delete(rule)
    session.flush()
    return True
