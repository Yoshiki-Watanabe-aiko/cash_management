import logging

import httpx

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 10.0
_STATUS_LABELS = {"success": "成功", "partial_success": "一部失敗", "failed": "失敗"}


def _post(webhook_url: str, content: str) -> None:
    if not webhook_url:
        logger.info("DISCORD_WEBHOOK_URL未設定のため通知をスキップします")
        return
    try:
        response = httpx.post(webhook_url, json={"content": content}, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Discord通知の送信に失敗しました: %s", exc)


def build_batch_summary_message(
    *,
    run_date: str,
    overall_status: str,
    step_results: list[dict],
    new_transaction_count: int,
    transfer_detected_count: int,
) -> str:
    status_label = _STATUS_LABELS.get(overall_status, overall_status)
    lines = [
        f"【日次バッチ結果】{run_date} — {status_label}",
        f"新規取込件数: {new_transaction_count} / 振替検知件数: {transfer_detected_count}",
        "",
    ]
    for step in step_results:
        step_label = _STATUS_LABELS.get(step["status"], step["status"])
        line = f"- {step['name']}: {step_label}"
        if step.get("detail"):
            line += f" ({step['detail']})"
        if step.get("error"):
            line += f" — {step['error']}"
        lines.append(line)
    return "\n".join(lines)


def send_batch_summary(
    webhook_url: str,
    *,
    run_date: str,
    overall_status: str,
    step_results: list[dict],
    new_transaction_count: int,
    transfer_detected_count: int,
) -> None:
    """日次バッチの機関別成否サマリーをDiscordへ送信する(ADR 0008)。Webhook未設定・送信失敗時も例外は送出しない。"""
    message = build_batch_summary_message(
        run_date=run_date,
        overall_status=overall_status,
        step_results=step_results,
        new_transaction_count=new_transaction_count,
        transfer_detected_count=transfer_detected_count,
    )
    _post(webhook_url, message)


def send_startup_failure(webhook_url: str, error: BaseException) -> None:
    """DB接続自体に失敗した致命的なケース向けの、DBを経由しない簡易通知(ADR 0008)。"""
    message = f"【日次バッチ】起動に失敗しました\n{type(error).__name__}: {error}"
    _post(webhook_url, message)
