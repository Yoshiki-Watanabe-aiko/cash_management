import datetime
import decimal

from sqlalchemy import select

from app.models import Account, AssetClass, AssetSnapshot, Institution


def _bank_institution_id(session) -> int:
    return session.execute(
        select(Institution.id).where(Institution.institution_name == "楽天銀行")
    ).scalar_one()


def test_net_worth_history_endpoint_returns_summed_points(client, db_session):
    account = Account(
        institution_id=_bank_institution_id(db_session),
        account_name="テストAPI純資産口座",
        account_type="bank",
        default_business_ratio=0,
        tracks_balance=True,
        balance_method="cumulative",
    )
    db_session.add(account)
    db_session.flush()

    cash_class_id = db_session.execute(
        select(AssetClass.id).where(AssetClass.asset_class_name == "現金")
    ).scalar_one()
    snapshot_date = datetime.date.today()
    db_session.add(
        AssetSnapshot(
            snapshot_date=snapshot_date,
            account_id=account.id,
            asset_class_id=cash_class_id,
            ticker_or_name=account.account_name,
            current_value=decimal.Decimal("12345"),
            source_type="cumulative",
        )
    )
    db_session.flush()

    response = client.get("/api/dashboard/net-worth-history?months=1")

    assert response.status_code == 200
    points = {item["snapshot_date"]: item["net_worth"] for item in response.json()}
    assert points[snapshot_date.isoformat()] == "12345.00"


def test_dashboard_endpoints_use_current_month_by_default(client):
    for path in (
        "/api/dashboard/budget-progress",
        "/api/dashboard/personal-cashflow",
        "/api/dashboard/category-breakdown",
    ):
        response = client.get(path)
        assert response.status_code == 200
