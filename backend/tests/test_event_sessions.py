from datetime import date, datetime, time
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.core import Event
from app.models.enums import EventSessionStatus
from app.schemas.event_form_schema import EventSessionCreate
from app.services.event_session_service import TRANSITIONS, _validate_payload


class _NoResponsibleDB:
    def scalar(self, _statement):
        return None


@pytest.fixture()
def event():
    return Event(
        id=uuid4(), client_id=uuid4(), name="Operational sessions",
        start_date=datetime(2026, 8, 1), end_date=datetime(2026, 8, 3),
    )


def test_session_schema_is_backwards_compatible():
    payload = EventSessionCreate(name="Show")
    assert payload.status == EventSessionStatus.PLANNED
    assert payload.expected_attendees == 0
    assert payload.responsible_id is None


def test_session_date_must_be_inside_event(event):
    with pytest.raises(HTTPException, match="within the event") as error:
        _validate_payload(_NoResponsibleDB(), event, {"session_date": date(2026, 8, 4)})
    assert error.value.status_code == 422


def test_session_end_time_must_be_after_start(event):
    with pytest.raises(HTTPException, match="after start") as error:
        _validate_payload(_NoResponsibleDB(), event, {"start_time": time(12), "end_time": time(11)})
    assert error.value.status_code == 422


def test_session_status_transitions_are_controlled():
    assert EventSessionStatus.READY in TRANSITIONS[EventSessionStatus.PLANNED]
    assert EventSessionStatus.COMPLETED not in TRANSITIONS[EventSessionStatus.PLANNED]
    assert TRANSITIONS[EventSessionStatus.COMPLETED] == set()
