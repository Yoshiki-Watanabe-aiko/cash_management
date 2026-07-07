import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_with_retry(
    func: Callable[[], T],
    *,
    step_name: str,
    retries: int,
    delay_seconds: float,
) -> T:
    """funcを実行し、例外発生時はretries回まで数秒間隔でリトライする(ADR 0008)。全て失敗したら最後の例外を送出する。"""
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 - リトライ判定のため意図的に広く捕捉
            last_error = exc
            logger.warning("%s: 試行%d/%d失敗: %s", step_name, attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay_seconds)

    assert last_error is not None
    raise last_error
