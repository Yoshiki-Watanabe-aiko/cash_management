import datetime

from app.core.business_days import business_days_between, is_business_day
from app.core.config import settings


def test_new_years_day_is_not_business_day():
    assert is_business_day(datetime.date(2026, 1, 1)) is False


def test_year_end_bank_holiday_is_not_business_day():
    assert is_business_day(datetime.date(2026, 12, 31)) is False


def test_saturday_is_not_business_day():
    assert is_business_day(datetime.date(2026, 7, 11)) is False


def test_jpholiday_is_not_business_day():
    assert is_business_day(datetime.date(2026, 11, 3)) is False


def test_ordinary_weekday_is_business_day():
    assert is_business_day(datetime.date(2026, 7, 8)) is True


def test_configured_long_holiday_is_not_business_day(monkeypatch):
    monkeypatch.setattr(settings, "long_holiday_start", "08-11")
    monkeypatch.setattr(settings, "long_holiday_end", "08-16")
    assert is_business_day(datetime.date(2026, 8, 13)) is False


def test_business_days_between_same_day_is_zero():
    d = datetime.date(2026, 7, 8)
    assert business_days_between(d, d) == 0


def test_business_days_between_counts_only_true_business_days():
    # 2026-07-10(金)〜2026-07-13(月, 祝日ではない通常営業日)の間は土日を挟むため1営業日
    start = datetime.date(2026, 7, 10)
    end = datetime.date(2026, 7, 13)
    assert business_days_between(start, end) == 1


def test_business_days_between_is_symmetric():
    a = datetime.date(2026, 7, 10)
    b = datetime.date(2026, 7, 13)
    assert business_days_between(a, b) == business_days_between(b, a)
