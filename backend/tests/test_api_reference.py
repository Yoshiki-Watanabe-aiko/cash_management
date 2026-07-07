from sqlalchemy import select

from app.models import Account, Institution


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def test_list_accounts_returns_seeded_and_created_accounts(client, db_session):
    institution_id = _bank_institution_id(db_session)
    account = Account(
        institution_id=institution_id,
        account_name="テストAPI口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
    )
    db_session.add(account)
    db_session.flush()

    response = client.get("/api/accounts")

    assert response.status_code == 200
    names = [item["account_name"] for item in response.json()]
    assert "テストAPI口座" in names


def test_list_categories_returns_seeded_categories(client):
    response = client.get("/api/categories")

    assert response.status_code == 200
    names = [item["category_name"] for item in response.json()]
    assert "食費" in names
