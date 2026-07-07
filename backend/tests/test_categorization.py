from app.models import Category, CategoryRule
from app.services.categorization import categorize


def _make_rule(session, category_name: str, keyword_pattern: str, priority: int) -> None:
    category = Category(category_name=category_name)
    session.add(category)
    session.flush()
    session.add(CategoryRule(keyword_pattern=keyword_pattern, category_id=category.id, priority=priority))
    session.flush()


def test_substring_match_applies_category(db_session):
    _make_rule(db_session, "テスト食費", "スーパー", priority=100)
    category_id = categorize(db_session, "スーパーマルエツ渋谷店")
    assert category_id is not None


def test_no_match_returns_none(db_session):
    _make_rule(db_session, "テスト食費2", "スーパー", priority=100)
    assert categorize(db_session, "映画館チケット") is None


def test_lower_priority_number_wins_on_conflicting_match(db_session):
    high_priority_category = Category(category_name="テスト優先カテゴリ")
    low_priority_category = Category(category_name="テスト非優先カテゴリ")
    db_session.add_all([high_priority_category, low_priority_category])
    db_session.flush()

    db_session.add_all(
        [
            CategoryRule(keyword_pattern="コンビニ", category_id=low_priority_category.id, priority=200),
            CategoryRule(keyword_pattern="コンビニ", category_id=high_priority_category.id, priority=10),
        ]
    )
    db_session.flush()

    category_id = categorize(db_session, "コンビニATM手数料")
    assert category_id == high_priority_category.id
