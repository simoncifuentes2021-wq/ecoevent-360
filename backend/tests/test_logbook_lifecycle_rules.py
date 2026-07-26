from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import require_roles
from app.models.enums import UserRole
from app.models.enums import LogbookInstanceStatus
from app.schemas.logbook_schema import InstanceCreate
from app.services.logbook_lifecycle_service import lifecycle_transitions

NOW = datetime(2026, 7, 25, 15, 0, tzinfo=UTC)


def instance(status, *, opens_at=None, due_at=None):
    return SimpleNamespace(status=status, opens_at=opens_at, due_at=due_at)


@pytest.mark.parametrize("delta", [-60, 0])
def test_scheduled_at_or_after_opening_opens(delta):
    item = instance(LogbookInstanceStatus.SCHEDULED, opens_at=NOW + timedelta(seconds=delta))
    assert [state for state, _ in lifecycle_transitions(item, NOW)] == [
        LogbookInstanceStatus.OPEN
    ]


def test_scheduled_before_opening_stays_scheduled():
    item = instance(LogbookInstanceStatus.SCHEDULED, opens_at=NOW + timedelta(seconds=1))
    assert lifecycle_transitions(item, NOW) == []


@pytest.mark.parametrize("delta", [-60, 0])
def test_open_at_or_after_deadline_becomes_overdue(delta):
    item = instance(LogbookInstanceStatus.OPEN, due_at=NOW + timedelta(seconds=delta))
    assert [state for state, _ in lifecycle_transitions(item, NOW)] == [
        LogbookInstanceStatus.OVERDUE
    ]


def test_open_before_deadline_stays_open():
    item = instance(LogbookInstanceStatus.OPEN, due_at=NOW + timedelta(seconds=1))
    assert lifecycle_transitions(item, NOW) == []


def test_delayed_scheduled_instance_records_both_transitions_in_order():
    item = instance(
        LogbookInstanceStatus.SCHEDULED,
        opens_at=NOW - timedelta(hours=2),
        due_at=NOW - timedelta(hours=1),
    )
    assert [state for state, _ in lifecycle_transitions(item, NOW)] == [
        LogbookInstanceStatus.OPEN,
        LogbookInstanceStatus.OVERDUE,
    ]


@pytest.mark.parametrize(
    "status",
    [
        LogbookInstanceStatus.IN_PROGRESS,
        LogbookInstanceStatus.UNDER_REVIEW,
        LogbookInstanceStatus.CHANGES_REQUESTED,
        LogbookInstanceStatus.COMPLETED,
        LogbookInstanceStatus.CANCELLED,
        LogbookInstanceStatus.OVERDUE,
    ],
)
def test_non_pending_states_are_never_changed(status):
    item = instance(status, opens_at=NOW - timedelta(days=2), due_at=NOW - timedelta(days=1))
    assert lifecycle_transitions(item, NOW) == []


def test_null_dates_are_skipped():
    assert lifecycle_transitions(instance(LogbookInstanceStatus.SCHEDULED), NOW) == []
    assert lifecycle_transitions(instance(LogbookInstanceStatus.OPEN), NOW) == []


def test_reference_time_must_be_timezone_aware():
    with pytest.raises(ValueError, match="timezone"):
        lifecycle_transitions(instance(LogbookInstanceStatus.OPEN, due_at=NOW), NOW.replace(tzinfo=None))


def test_instance_dates_must_include_timezone():
    from uuid import uuid4

    with pytest.raises(ValueError, match="timezone"):
        InstanceCreate(
            template_version_id=uuid4(),
            assignment_mode="INDIVIDUAL",
            participant_ids=[uuid4()],
            opens_at=NOW.replace(tzinfo=None),
        )


def test_chilean_dst_instants_compare_as_absolute_time():
    from zoneinfo import ZoneInfo

    chile = ZoneInfo("America/Santiago")
    opening = datetime(2026, 9, 6, 1, 30, tzinfo=chile)
    reference = opening.astimezone(UTC)
    item = instance(LogbookInstanceStatus.SCHEDULED, opens_at=opening)
    assert lifecycle_transitions(item, reference)[0][0] == LogbookInstanceStatus.OPEN


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.SUPER_ADMIN])
def test_administrators_can_invoke_manual_processing(role):
    dependency = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    current = SimpleNamespace(role=role)
    assert dependency(current_user=current) is current


@pytest.mark.parametrize(
    "role",
    [UserRole.CLIENT, UserRole.WORKER, UserRole.LOGISTICS_OPERATOR, UserRole.SUPERVISOR],
)
def test_non_administrators_cannot_invoke_manual_processing(role):
    dependency = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    with pytest.raises(HTTPException) as error:
        dependency(current_user=SimpleNamespace(role=role))
    assert error.value.status_code == 403
