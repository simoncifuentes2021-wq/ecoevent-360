from datetime import UTC, date, datetime, timedelta

from app.core.time import CHILE_TIMEZONE, chile_day_utc_bounds_naive


def test_chile_timezone_uses_summer_and_winter_offsets():
    assert datetime(2026, 1, 15, 12, tzinfo=CHILE_TIMEZONE).utcoffset() == timedelta(hours=-3)
    assert datetime(2026, 7, 15, 12, tzinfo=CHILE_TIMEZONE).utcoffset() == timedelta(hours=-4)


def test_chile_day_is_converted_to_utc_storage_bounds():
    start, end = chile_day_utc_bounds_naive(date(2026, 7, 15))
    assert start == datetime(2026, 7, 15, 4)
    assert end == datetime(2026, 7, 16, 3, 59, 59, 999999)
    assert start.replace(tzinfo=UTC).astimezone(CHILE_TIMEZONE).date() == date(2026, 7, 15)
