"""Canonical clock and timezone helpers for EcoEvent 360."""
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

CHILE_TIMEZONE_NAME = "America/Santiago"
CHILE_TIMEZONE = ZoneInfo(CHILE_TIMEZONE_NAME)


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    return utc_now().replace(tzinfo=None)


def chile_now() -> datetime:
    return utc_now().astimezone(CHILE_TIMEZONE)


def chile_today() -> date:
    return chile_now().date()


def chile_day_utc_bounds_naive(day: date | None = None) -> tuple[datetime, datetime]:
    local_day = day or chile_today()
    start_local = datetime.combine(local_day, time.min, tzinfo=CHILE_TIMEZONE)
    end_local = datetime.combine(local_day, time.max, tzinfo=CHILE_TIMEZONE)
    return (
        start_local.astimezone(UTC).replace(tzinfo=None),
        end_local.astimezone(UTC).replace(tzinfo=None),
    )
