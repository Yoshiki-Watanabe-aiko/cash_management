from sqlalchemy import select

from app.models import Category, CategoryRule


def _category_id(session, name: str) -> int:
    return session.execute(select(Category.id).where(Category.category_name == name)).scalar_one()


def test_post_category_rule_creates_new_rule(client, db_session):
    category_id = _category_id(db_session, "食費")

    response = client.post(
        "/api/category-rules", json={"keyword_pattern": "スーパー", "category_id": category_id, "priority": 10}
    )

    assert response.status_code == 201
    assert response.json()["keyword_pattern"] == "スーパー"


def test_post_category_rule_returns_400_on_unknown_category(client):
    response = client.post(
        "/api/category-rules", json={"keyword_pattern": "コンビニ", "category_id": 999999999, "priority": 10}
    )
    assert response.status_code == 400


def test_get_category_rules_orders_by_priority(client, db_session):
    category_id = _category_id(db_session, "交通費")
    client.post("/api/category-rules", json={"keyword_pattern": "タクシー", "category_id": category_id, "priority": 90})
    client.post("/api/category-rules", json={"keyword_pattern": "電車", "category_id": category_id, "priority": 3})

    response = client.get("/api/category-rules")

    assert response.status_code == 200
    patterns = [item["keyword_pattern"] for item in response.json()]
    assert patterns.index("電車") < patterns.index("タクシー")


def test_patch_category_rule_updates_priority(client, db_session):
    category_id = _category_id(db_session, "通信費")
    created = client.post(
        "/api/category-rules", json={"keyword_pattern": "携帯", "category_id": category_id, "priority": 20}
    ).json()

    response = client.patch(f"/api/category-rules/{created['id']}", json={"priority": 1})

    assert response.status_code == 200
    assert response.json()["priority"] == 1


def test_patch_category_rule_returns_400_on_unknown_category(client, db_session):
    category_id = _category_id(db_session, "保険料")
    created = client.post(
        "/api/category-rules", json={"keyword_pattern": "保険", "category_id": category_id, "priority": 20}
    ).json()

    response = client.patch(f"/api/category-rules/{created['id']}", json={"category_id": 999999999})

    assert response.status_code == 400


def test_patch_category_rule_returns_404_when_not_found(client):
    response = client.patch("/api/category-rules/999999999", json={"priority": 1})
    assert response.status_code == 404


def test_patch_category_rule_returns_400_when_keyword_pattern_is_null(client, db_session):
    category_id = _category_id(db_session, "食費")
    created = client.post(
        "/api/category-rules", json={"keyword_pattern": "NULL検証", "category_id": category_id, "priority": 20}
    ).json()

    response = client.patch(f"/api/category-rules/{created['id']}", json={"keyword_pattern": None})

    assert response.status_code == 400


def test_delete_category_rule_removes_row(client, db_session):
    category_id = _category_id(db_session, "医療費")
    created = client.post(
        "/api/category-rules", json={"keyword_pattern": "薬局", "category_id": category_id, "priority": 20}
    ).json()

    response = client.delete(f"/api/category-rules/{created['id']}")

    assert response.status_code == 204
    assert db_session.get(CategoryRule, created["id"]) is None


def test_delete_category_rule_returns_404_when_not_found(client):
    response = client.delete("/api/category-rules/999999999")
    assert response.status_code == 404
