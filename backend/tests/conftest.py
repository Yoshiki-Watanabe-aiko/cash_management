import pytest
from sqlalchemy.orm import Session

from app.db.session import engine


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
