import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """本物のPostgreSQLに接続しつつ、テストごとにSAVEPOINTでロールバックしてデータを残さない。"""
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    """db_sessionのSAVEPOINTトランザクション内でAPIを呼び出すTestClient(commit/rollbackはテスト側が制御)。"""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
