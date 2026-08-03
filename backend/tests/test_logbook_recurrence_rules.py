from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.enums import (
    LogbookAssignmentStatus,
    LogbookInstanceStatus,
    LogbookRecurrenceEndMode,
    LogbookRecurrenceFrequency,
)
from app.schemas.logbook_schema import RecurrencePreviewIn
from app.services.logbook_recurrence_service import calculate_occurrence_dates, preview
from app.services.logbook_service import ensure_logbook_editable


def rule(**overrides):
    values = dict(
        frequency=LogbookRecurrenceFrequency.WEEKLY,
        interval=1,
        weekdays=[1],
        day_of_month=None,
        start_date=date(2026, 8, 1),
        end_mode=LogbookRecurrenceEndMode.COUNT,
        end_date=None,
        max_occurrences=5,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_weekly_tuesdays_and_inclusive_end_date():
    dates, truncated = calculate_occurrence_dates(rule(
        end_mode=LogbookRecurrenceEndMode.END_DATE,
        end_date=date(2026, 8, 25), max_occurrences=None,
    ))
    assert dates == [date(2026, 8, 4), date(2026, 8, 11), date(2026, 8, 18), date(2026, 8, 25)]
    assert not truncated


def test_multiple_weekdays_and_every_two_weeks():
    dates, _ = calculate_occurrence_dates(rule(interval=2, weekdays=[0, 4], max_occurrences=4))
    assert dates == [date(2026, 8, 3), date(2026, 8, 7), date(2026, 8, 17), date(2026, 8, 21)]


def test_daily_crosses_year_boundary():
    dates, _ = calculate_occurrence_dates(rule(
        frequency=LogbookRecurrenceFrequency.DAILY, interval=2, weekdays=None,
        start_date=date(2026, 12, 30), max_occurrences=3,
    ))
    assert dates == [date(2026, 12, 30), date(2027, 1, 1), date(2027, 1, 3)]


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (29, [date(2024, 1, 29), date(2024, 2, 29), date(2024, 3, 29)]),
        (30, [date(2024, 1, 30), date(2024, 3, 30), date(2024, 4, 30)]),
        (31, [date(2024, 1, 31), date(2024, 3, 31), date(2024, 5, 31)]),
    ],
)
def test_monthly_skips_months_without_selected_day(day, expected):
    dates, _ = calculate_occurrence_dates(rule(
        frequency=LogbookRecurrenceFrequency.MONTHLY, weekdays=None,
        day_of_month=day, start_date=date(2024, 1, day), max_occurrences=3,
    ))
    assert dates == expected


def test_preview_is_non_persistent_and_uses_chile_timezone():
    result = preview(RecurrencePreviewIn(
        frequency="WEEKLY", interval=1, weekdays=[1], start_date="2026-08-01",
        end_mode="COUNT", max_occurrences=2, opens_at_local="09:00",
        due_at_local="18:00", timezone="America/Santiago", limit=12,
    ))
    assert result == {"dates": [date(2026, 8, 4), date(2026, 8, 11)], "truncated": False}


@pytest.mark.parametrize("status", [
    LogbookInstanceStatus.SCHEDULED,
    LogbookInstanceStatus.UNDER_REVIEW,
    LogbookInstanceStatus.COMPLETED,
    LogbookInstanceStatus.CANCELLED,
    LogbookInstanceStatus.OVERDUE,
])
def test_mutations_are_blocked_for_non_editable_instance_states(status):
    with pytest.raises(HTTPException) as exc:
        ensure_logbook_editable(
            SimpleNamespace(status=status),
            SimpleNamespace(status=LogbookAssignmentStatus.IN_PROGRESS),
        )
    assert exc.value.status_code == 409


def test_changes_requested_is_limited_to_correcting_participant():
    with pytest.raises(HTTPException) as exc:
        ensure_logbook_editable(
            SimpleNamespace(status=LogbookInstanceStatus.CHANGES_REQUESTED),
            SimpleNamespace(status=LogbookAssignmentStatus.IN_PROGRESS),
        )
    assert exc.value.status_code == 403
