import pytest

from app.cli import run_daily_import


class _FakeSessionContextManager:
    """SessionLocal()の`with ... as session:`をモックするためのダミーコンテキストマネージャ。"""

    def __init__(self, session: object) -> None:
        self._session = session

    def __enter__(self) -> object:
        return self._session

    def __exit__(self, *_exc_info: object) -> None:
        return None


def _make_batch_log(status: str) -> object:
    return type(
        "FakeBatchLog",
        (),
        {
            "status": status,
            "new_transaction_count": 3,
            "transfer_detected_count": 1,
            "institution_results": [{"name": "楽天銀行", "status": status, "detail": "ok"}],
        },
    )()


def test_main_success_does_not_exit(monkeypatch):
    """run_daily_batchが正常終了(status=success)した場合、main()はSystemExitを発生させない。"""
    monkeypatch.setattr(run_daily_import, "setup_logging", lambda: None)
    monkeypatch.setattr(run_daily_import, "SessionLocal", lambda: _FakeSessionContextManager(object()))
    monkeypatch.setattr(
        run_daily_import, "run_daily_batch", lambda session: _make_batch_log("success")
    )

    run_daily_import.main()


def test_main_exits_with_1_when_batch_log_status_is_failed(monkeypatch):
    """run_daily_batchが例外を送出せず正常に返ってきても、status=failedならexit code 1で終了する。"""
    monkeypatch.setattr(run_daily_import, "setup_logging", lambda: None)
    monkeypatch.setattr(run_daily_import, "SessionLocal", lambda: _FakeSessionContextManager(object()))
    monkeypatch.setattr(
        run_daily_import, "run_daily_batch", lambda session: _make_batch_log("failed")
    )

    with pytest.raises(SystemExit) as exc_info:
        run_daily_import.main()

    assert exc_info.value.code == 1


def test_main_sends_startup_failure_and_exits_when_db_connection_fails(monkeypatch):
    """SessionLocal()やrun_daily_batchが例外を送出する致命的なケースでは、
    DBを経由しない簡易Discord通知(send_startup_failure)を送りexit code 1で終了する。"""
    monkeypatch.setattr(run_daily_import, "setup_logging", lambda: None)

    def _raise_connection_error():
        raise ConnectionError("DB接続に失敗しました")

    monkeypatch.setattr(run_daily_import, "SessionLocal", _raise_connection_error)

    sent_calls: list[tuple[str, BaseException]] = []
    monkeypatch.setattr(
        run_daily_import,
        "send_startup_failure",
        lambda webhook_url, error: sent_calls.append((webhook_url, error)),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_daily_import.main()

    assert exc_info.value.code == 1
    assert len(sent_calls) == 1
    assert isinstance(sent_calls[0][1], ConnectionError)


def test_main_logs_each_institution_result(monkeypatch, caplog):
    """成功時、機関ごとの結果(institution_results)がすべてログ出力される。"""
    monkeypatch.setattr(run_daily_import, "setup_logging", lambda: None)
    monkeypatch.setattr(run_daily_import, "SessionLocal", lambda: _FakeSessionContextManager(object()))
    monkeypatch.setattr(
        run_daily_import, "run_daily_batch", lambda session: _make_batch_log("success")
    )

    with caplog.at_level("INFO", logger=run_daily_import.logger.name):
        run_daily_import.main()

    assert any("楽天銀行" in record.message for record in caplog.records)
