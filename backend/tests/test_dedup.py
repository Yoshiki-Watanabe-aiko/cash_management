import datetime
import decimal

from app.services.dedup import compute_source_hash


def test_hash_is_64_char_hex():
    h = compute_source_hash(1, datetime.date(2026, 7, 1), decimal.Decimal("-1500"), "スーパーA", "mf-1")
    assert len(h) == 64
    int(h, 16)  # 16進として解釈できること


def test_same_inputs_produce_same_hash():
    args = (1, datetime.date(2026, 7, 1), decimal.Decimal("-1500.00"), "スーパーA", "mf-1")
    assert compute_source_hash(*args) == compute_source_hash(*args)


def test_different_source_unique_id_changes_hash():
    """同一店舗・同日・同額の別取引はsource_unique_idの違いで区別される(ADR 0003)。"""
    h1 = compute_source_hash(1, datetime.date(2026, 7, 1), decimal.Decimal("-1500"), "スーパーA", "mf-1")
    h2 = compute_source_hash(1, datetime.date(2026, 7, 1), decimal.Decimal("-1500"), "スーパーA", "mf-2")
    assert h1 != h2


def test_none_account_id_does_not_raise():
    h = compute_source_hash(None, datetime.date(2026, 7, 1), decimal.Decimal("-1500"), "スーパーA", "mf-1")
    assert len(h) == 64


def test_decimal_scale_normalization_does_not_change_hash():
    h1 = compute_source_hash(1, datetime.date(2026, 7, 1), decimal.Decimal("1500"), "内容", "id1")
    h2 = compute_source_hash(1, datetime.date(2026, 7, 1), decimal.Decimal("1500.00"), "内容", "id1")
    assert h1 == h2
