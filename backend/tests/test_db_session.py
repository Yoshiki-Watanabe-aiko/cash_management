import pytest

from app.db import session as session_module


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def commit(self) -> None:
        self.calls.append("commit")

    def rollback(self) -> None:
        self.calls.append("rollback")

    def close(self) -> None:
        self.calls.append("close")


def test_get_db_commits_and_closes_on_success(monkeypatch):
    """例外なく処理が完了した場合、get_db()はcommit()してからclose()する。"""
    fake_session = _FakeSession()
    monkeypatch.setattr(session_module, "SessionLocal", lambda: fake_session)

    generator = session_module.get_db()
    db = next(generator)
    assert db is fake_session

    with pytest.raises(StopIteration):
        next(generator)

    assert fake_session.calls == ["commit", "close"]


def test_get_db_rolls_back_and_closes_on_exception(monkeypatch):
    """呼び出し元で例外が発生した場合、get_db()はcommit()せずrollback()してからclose()し、例外を再送出する。"""
    fake_session = _FakeSession()
    monkeypatch.setattr(session_module, "SessionLocal", lambda: fake_session)

    generator = session_module.get_db()
    next(generator)

    with pytest.raises(ValueError, match="boom"):
        generator.throw(ValueError("boom"))

    assert fake_session.calls == ["rollback", "close"]
