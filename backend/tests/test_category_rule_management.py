import pytest
from sqlalchemy import select

from app.models import Category, CategoryRule
from app.services import category_rule_management
from app.services.category_rule_management import CategoryRuleValidationError


def _category_id(session, name: str) -> int:
    return session.execute(select(Category.id).where(Category.category_name == name)).scalar_one()


def test_create_category_rule_persists_new_row(db_session):
    category_id = _category_id(db_session, "食費")

    rule = category_rule_management.create_category_rule(
        db_session, keyword_pattern="スーパー", category_id=category_id, priority=10
    )

    assert rule.id is not None
    assert db_session.get(CategoryRule, rule.id).keyword_pattern == "スーパー"


def test_create_category_rule_rejects_unknown_category(db_session):
    with pytest.raises(CategoryRuleValidationError):
        category_rule_management.create_category_rule(
            db_session, keyword_pattern="コンビニ", category_id=999999999, priority=10
        )


def test_list_category_rules_orders_by_priority(db_session):
    category_id = _category_id(db_session, "交通費")
    category_rule_management.create_category_rule(
        db_session, keyword_pattern="タクシー", category_id=category_id, priority=50
    )
    category_rule_management.create_category_rule(
        db_session, keyword_pattern="電車", category_id=category_id, priority=5
    )

    rules = category_rule_management.list_category_rules(db_session)
    patterns = [rule.keyword_pattern for rule in rules]

    assert patterns.index("電車") < patterns.index("タクシー")


def test_update_category_rule_changes_fields(db_session):
    category_id = _category_id(db_session, "通信費")
    rule = category_rule_management.create_category_rule(
        db_session, keyword_pattern="携帯", category_id=category_id, priority=20
    )

    updated = category_rule_management.update_category_rule(db_session, rule.id, {"priority": 1})

    assert updated.priority == 1


def test_update_category_rule_rejects_unknown_category(db_session):
    category_id = _category_id(db_session, "水道光熱費")
    rule = category_rule_management.create_category_rule(
        db_session, keyword_pattern="電気", category_id=category_id, priority=20
    )

    with pytest.raises(CategoryRuleValidationError):
        category_rule_management.update_category_rule(db_session, rule.id, {"category_id": 999999999})


def test_update_category_rule_returns_none_when_not_found(db_session):
    result = category_rule_management.update_category_rule(db_session, 999999999, {"priority": 1})
    assert result is None


@pytest.mark.parametrize("field", ["keyword_pattern", "category_id", "priority"])
def test_update_category_rule_rejects_null_on_not_nullable_field(db_session, field):
    category_id = _category_id(db_session, "食費")
    rule = category_rule_management.create_category_rule(
        db_session, keyword_pattern="NULL検証", category_id=category_id, priority=20
    )

    with pytest.raises(CategoryRuleValidationError):
        category_rule_management.update_category_rule(db_session, rule.id, {field: None})


def test_delete_category_rule_removes_row(db_session):
    category_id = _category_id(db_session, "医療費")
    rule = category_rule_management.create_category_rule(
        db_session, keyword_pattern="薬局", category_id=category_id, priority=20
    )

    deleted = category_rule_management.delete_category_rule(db_session, rule.id)

    assert deleted is True
    assert db_session.get(CategoryRule, rule.id) is None


def test_delete_category_rule_returns_false_when_not_found(db_session):
    assert category_rule_management.delete_category_rule(db_session, 999999999) is False
