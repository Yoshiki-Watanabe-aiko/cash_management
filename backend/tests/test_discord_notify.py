import httpx

from app.services.discord_notify import (
    build_batch_summary_message,
    send_batch_summary,
    send_startup_failure,
)


def test_build_batch_summary_message_includes_status_and_steps():
    message = build_batch_summary_message(
        run_date="2026-07-08",
        overall_status="partial_success",
        step_results=[
            {"name": "MFME取引明細CSV取込", "status": "success", "detail": "ファイル1件・新規2件", "error": None},
            {"name": "カードメール取込(個人用)", "status": "failed", "detail": "", "error": "IMAP接続失敗"},
        ],
        new_transaction_count=2,
        transfer_detected_count=0,
    )

    assert "2026-07-08" in message
    assert "一部失敗" in message
    assert "MFME取引明細CSV取込: 成功 (ファイル1件・新規2件)" in message
    assert "カードメール取込(個人用): 失敗 — IMAP接続失敗" in message


def test_send_batch_summary_skips_when_webhook_url_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append((a, k)))

    send_batch_summary(
        "",
        run_date="2026-07-08",
        overall_status="success",
        step_results=[],
        new_transaction_count=0,
        transfer_detected_count=0,
    )

    assert calls == []


def test_send_batch_summary_posts_to_webhook(monkeypatch):
    posted = {}

    class _Response:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        posted["url"] = url
        posted["json"] = json
        return _Response()

    monkeypatch.setattr(httpx, "post", fake_post)

    send_batch_summary(
        "https://discord.example/webhook",
        run_date="2026-07-08",
        overall_status="success",
        step_results=[{"name": "振替検知", "status": "success", "detail": "1件", "error": None}],
        new_transaction_count=3,
        transfer_detected_count=1,
    )

    assert posted["url"] == "https://discord.example/webhook"
    assert "振替検知" in posted["json"]["content"]


def test_send_batch_summary_does_not_raise_on_http_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "post", fake_post)

    send_batch_summary(
        "https://discord.example/webhook",
        run_date="2026-07-08",
        overall_status="failed",
        step_results=[],
        new_transaction_count=0,
        transfer_detected_count=0,
    )


def test_send_startup_failure_does_not_raise_when_webhook_missing():
    send_startup_failure("", RuntimeError("DB接続失敗"))
