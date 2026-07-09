from sqlalchemy import select

from app.models import Institution


def _institution_id(session, name: str) -> int:
    return session.execute(select(Institution.id).where(Institution.institution_name == name)).scalar_one()


def test_post_account_creates_new_account(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    response = client.post(
        "/api/accounts",
        json={
            "institution_id": institution_id,
            "account_name": "テストAPI口座作成A",
            "account_type": "bank",
            "is_business": False,
            "tracks_balance": True,
            "balance_method": "cumulative",
            "opening_balance": "100000",
            "opening_balance_date": "2026-07-01",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["account_name"] == "テストAPI口座作成A"
    assert body["institution_id"] == institution_id


def test_post_account_returns_400_on_invalid_account_type(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    response = client.post(
        "/api/accounts",
        json={"institution_id": institution_id, "account_name": "テストAPI口座作成B", "account_type": "crypto"},
    )

    assert response.status_code == 400


def test_post_account_returns_400_when_tracking_balance_without_method(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")

    response = client.post(
        "/api/accounts",
        json={
            "institution_id": institution_id,
            "account_name": "テストAPI口座作成C",
            "account_type": "bank",
            "tracks_balance": True,
        },
    )

    assert response.status_code == 400


def test_patch_account_toggles_is_active(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    created = client.post(
        "/api/accounts",
        json={"institution_id": institution_id, "account_name": "テストAPI口座更新A", "account_type": "bank"},
    ).json()

    response = client.patch(f"/api/accounts/{created['id']}", json={"is_active": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_patch_account_returns_400_on_invalid_update(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    created = client.post(
        "/api/accounts",
        json={"institution_id": institution_id, "account_name": "テストAPI口座更新B", "account_type": "bank"},
    ).json()

    response = client.patch(f"/api/accounts/{created['id']}", json={"institution_id": 999999999})

    assert response.status_code == 400


def test_patch_account_returns_404_when_not_found(client):
    response = client.patch("/api/accounts/999999999", json={"is_active": False})
    assert response.status_code == 404


def test_patch_account_returns_400_when_account_name_is_null(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    created = client.post(
        "/api/accounts",
        json={"institution_id": institution_id, "account_name": "テストAPI口座NULL検証", "account_type": "bank"},
    ).json()

    response = client.patch(f"/api/accounts/{created['id']}", json={"account_name": None})

    assert response.status_code == 400


def test_get_accounts_includes_full_detail_fields(client, db_session):
    institution_id = _institution_id(db_session, "楽天銀行")
    client.post(
        "/api/accounts",
        json={"institution_id": institution_id, "account_name": "テストAPI口座一覧A", "account_type": "bank"},
    )

    response = client.get("/api/accounts")

    assert response.status_code == 200
    matching = [item for item in response.json() if item["account_name"] == "テストAPI口座一覧A"]
    assert len(matching) == 1
    assert matching[0]["institution_id"] == institution_id


def test_get_institutions_returns_seeded_institutions(client):
    response = client.get("/api/institutions")

    assert response.status_code == 200
    names = {item["institution_name"] for item in response.json()}
    assert "楽天銀行" in names
