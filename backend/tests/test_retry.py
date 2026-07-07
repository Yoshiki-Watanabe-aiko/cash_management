import pytest

from app.services.retry import run_with_retry


def test_run_with_retry_returns_result_on_first_success():
    calls = []

    def func():
        calls.append(1)
        return "ok"

    result = run_with_retry(func, step_name="test", retries=3, delay_seconds=0)

    assert result == "ok"
    assert len(calls) == 1


def test_run_with_retry_retries_until_success(monkeypatch):
    monkeypatch.setattr("app.services.retry.time.sleep", lambda _: None)
    calls = []

    def func():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("transient")
        return "recovered"

    result = run_with_retry(func, step_name="test", retries=3, delay_seconds=0)

    assert result == "recovered"
    assert len(calls) == 3


def test_run_with_retry_raises_last_error_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("app.services.retry.time.sleep", lambda _: None)
    calls = []

    def func():
        calls.append(1)
        raise ValueError(f"failure-{len(calls)}")

    with pytest.raises(ValueError, match="failure-3"):
        run_with_retry(func, step_name="test", retries=3, delay_seconds=0)

    assert len(calls) == 3
