import decimal

from sqlalchemy import select

from app.models import Budget, Category


def _category_id(session, name: str) -> int:
    return session.execute(select(Category.id).where(Category.category_name == name)).scalar_one()


def test_post_budget_creates_new_budget(client, db_session):
    category_id = _category_id(db_session, "食費")

    response = client.post(
        "/api/budgets",
        json={
            "category_id": category_id,
            "year_month": "2026-07",
            "is_business": False,
            "budget_amount": "30000",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert decimal.Decimal(body["budget_amount"]) == decimal.Decimal("30000")
    assert body["category_id"] == category_id


def test_post_budget_returns_400_on_duplicate(client, db_session):
    category_id = _category_id(db_session, "交通費")
    client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-07", "is_business": True, "budget_amount": "10000"},
    )

    response = client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-07", "is_business": True, "budget_amount": "20000"},
    )

    assert response.status_code == 400


def test_post_budget_returns_422_on_invalid_year_month(client, db_session):
    category_id = _category_id(db_session, "通信費")

    response = client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-13", "is_business": True, "budget_amount": "1000"},
    )

    assert response.status_code == 422


def test_get_budgets_filters_by_query_params(client, db_session):
    category_id = _category_id(db_session, "水道光熱費")
    client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-08", "is_business": True, "budget_amount": "5000"},
    )

    response = client.get("/api/budgets?year_month=2026-08&is_business=true")

    assert response.status_code == 200
    assert any(item["category_id"] == category_id for item in response.json())


def test_patch_budget_updates_amount(client, db_session):
    category_id = _category_id(db_session, "医療費")
    created = client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-09", "is_business": False, "budget_amount": "4000"},
    ).json()

    response = client.patch(f"/api/budgets/{created['id']}", json={"budget_amount": "4500"})

    assert response.status_code == 200
    assert decimal.Decimal(response.json()["budget_amount"]) == decimal.Decimal("4500")


def test_patch_budget_returns_404_when_not_found(client):
    response = client.patch("/api/budgets/999999999", json={"budget_amount": "1000"})
    assert response.status_code == 404


def test_delete_budget_removes_row(client, db_session):
    category_id = _category_id(db_session, "保険料")
    created = client.post(
        "/api/budgets",
        json={"category_id": category_id, "year_month": "2026-10", "is_business": True, "budget_amount": "6000"},
    ).json()

    response = client.delete(f"/api/budgets/{created['id']}")

    assert response.status_code == 204
    assert db_session.get(Budget, created["id"]) is None


def test_delete_budget_returns_404_when_not_found(client):
    response = client.delete("/api/budgets/999999999")
    assert response.status_code == 404
