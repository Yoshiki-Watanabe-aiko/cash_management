import datetime

import jpholiday

from app.core.config import settings

_YEAR_END_NEW_YEAR_MONTH_DAYS: frozenset[tuple[int, int]] = frozenset(
    {(12, 31), (1, 1), (1, 2), (1, 3)}
)


def _parse_month_day(value: str) -> tuple[int, int] | None:
    if not value:
        return None
    month_str, _, day_str = value.partition("-")
    return int(month_str), int(day_str)


def _in_configured_long_holiday(d: datetime.date) -> bool:
    start = _parse_month_day(settings.long_holiday_start)
    end = _parse_month_day(settings.long_holiday_end)
    if start is None or end is None:
        return False
    month_day = (d.month, d.day)
    if start <= end:
        return start <= month_day <= end
    return month_day >= start or month_day <= end


def is_business_day(d: datetime.date) -> bool:
    """真の営業日判定(土日・日本の祝日・年末年始12/31-1/3・設定済み長期休暇を除外)。"""
    if d.weekday() >= 5:
        return False
    if jpholiday.is_holiday(d):
        return False
    if (d.month, d.day) in _YEAR_END_NEW_YEAR_MONTH_DAYS:
        return False
    if _in_configured_long_holiday(d):
        return False
    return True


def business_days_between(date_a: datetime.date, date_b: datetime.date) -> int:
    """2つの日付間にある真の営業日の日数(同日なら0)。"""
    start, end = min(date_a, date_b), max(date_a, date_b)
    count = 0
    current = start + datetime.timedelta(days=1)
    while current <= end:
        if is_business_day(current):
            count += 1
        current += datetime.timedelta(days=1)
    return count
