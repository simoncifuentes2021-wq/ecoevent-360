from datetime import date, datetime, time, timedelta
from io import BytesIO
import os
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, delete, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventSessionStaff, EventStaff, Evidence, Incident, Task, User
from app.models.enums import EventStatus, UserRole
from app.schemas.event_form_schema import EventSessionCreate
from app.schemas.event_session_staff_schema import EventSessionStaffCreate, EventSessionStaffUpdate
from app.schemas.event_session_staff_schema import EventSessionStaffRead
from app.schemas.evidence_schema import EvidenceRead
from app.schemas.incident_schema import IncidentCorrectiveTaskCreate, IncidentCreate, IncidentUpdate
from app.schemas.task_schema import TaskCreate, TaskUpdate
from app.services import evidence_service, event_session_service, event_session_staff_service, incident_service, task_service


@pytest.fixture()
def context():
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    clients = [Client(business_name=f"1B {suffix}"), Client(business_name=f"Other {suffix}")]
    db.add_all(clients)
    db.flush()
    users = {
        "admin": User(full_name="Admin", email=f"a-{suffix}@test.dev", password_hash="x", role=UserRole.ADMIN),
        "superadmin": User(full_name="Super", email=f"sa-{suffix}@test.dev", password_hash="x", role=UserRole.SUPER_ADMIN),
        "supervisor": User(full_name="Supervisor", email=f"s-{suffix}@test.dev", password_hash="x", role=UserRole.SUPERVISOR),
        "worker": User(full_name="Worker", email=f"w-{suffix}@test.dev", password_hash="x", role=UserRole.WORKER),
        "logistics": User(full_name="Logistics", email=f"l-{suffix}@test.dev", password_hash="x", role=UserRole.LOGISTICS_OPERATOR),
        "client": User(full_name="Client", email=f"c-{suffix}@test.dev", password_hash="x", role=UserRole.CLIENT, client_id=clients[0].id),
        "other": User(full_name="Other", email=f"o-{suffix}@test.dev", password_hash="x", role=UserRole.WORKER),
    }
    db.add_all(users.values())
    db.flush()
    start = datetime(2026, 8, 10, 8)
    events = [
        Event(client_id=clients[0].id, name="Event", start_date=start, end_date=start + timedelta(days=2), status=EventStatus.PLANNING),
        Event(client_id=clients[1].id, name="Other", start_date=start, end_date=start + timedelta(days=2), status=EventStatus.PLANNING),
    ]
    db.add_all(events)
    db.flush()
    staff = {
        "supervisor": EventStaff(event_id=events[0].id, user_id=users["supervisor"].id),
        "worker": EventStaff(event_id=events[0].id, user_id=users["worker"].id),
        "logistics": EventStaff(event_id=events[0].id, user_id=users["logistics"].id),
        "other": EventStaff(event_id=events[1].id, user_id=users["other"].id),
    }
    db.add_all(staff.values())
    db.commit()
    shows = [
        event_session_service.create_session(db, events[0].id, EventSessionCreate(name="Show A", session_date=date(2026, 8, 10), start_time=time(10), end_time=time(12)), users["admin"]),
        event_session_service.create_session(db, events[0].id, EventSessionCreate(name="Show B", session_date=date(2026, 8, 10), start_time=time(11), end_time=time(13)), users["admin"]),
        event_session_service.create_session(db, events[1].id, EventSessionCreate(name="Other show"), users["admin"]),
    ]
    try:
        yield db, events, users, staff, shows
    finally:
        db.rollback()
        db.execute(delete(AuditLog).where(AuditLog.event_id.in_([event.id for event in events])))
        db.execute(delete(Event).where(Event.id.in_([event.id for event in events])))
        db.execute(delete(User).where(User.id.in_([user.id for user in users.values()])))
        db.execute(delete(Client).where(Client.id.in_([client.id for client in clients])))
        db.commit()
        db.close()


def test_show_staff_integrity_overlap_update_and_remove(context):
    db, events, users, staff, shows = context
    first = event_session_staff_service.create_assignment(db, shows[0].id, EventSessionStaffCreate(event_staff_id=staff["worker"].id, shift_start=datetime(2026, 8, 10, 10), shift_end=datetime(2026, 8, 10, 12)), users["admin"])
    second = event_session_staff_service.create_assignment(db, shows[1].id, EventSessionStaffCreate(event_staff_id=staff["worker"].id, shift_start=datetime(2026, 8, 10, 11), shift_end=datetime(2026, 8, 10, 13)), users["admin"])
    assert second.overlap_warning is True
    with pytest.raises(HTTPException, match="already assigned"):
        event_session_staff_service.create_assignment(db, shows[0].id, EventSessionStaffCreate(event_staff_id=staff["worker"].id), users["admin"])
    with pytest.raises(HTTPException, match="does not belong"):
        event_session_staff_service.create_assignment(db, shows[0].id, EventSessionStaffCreate(event_staff_id=staff["other"].id), users["admin"])
    changed = event_session_staff_service.update_assignment(db, first.id, EventSessionStaffUpdate(operational_role="Stage manager"), users["supervisor"])
    assert changed.operational_role == "Stage manager"
    event_session_staff_service.delete_assignment(db, changed.id, users["admin"])
    assert db.get(EventSessionStaff, changed.id) is None


def test_show_staff_shift_timezone_normalization_and_response_context(context):
    db, _, users, staff, shows = context
    payload = EventSessionStaffCreate(
        event_staff_id=staff["worker"].id,
        shift_start="2026-08-10T06:00:00-04:00",
        shift_end="2026-08-10T12:00:00Z",
    )
    assert payload.shift_start == datetime(2026, 8, 10, 10)
    assert payload.shift_end == datetime(2026, 8, 10, 12)
    item = event_session_staff_service.create_assignment(db, shows[0].id, payload, users["admin"])
    assert item.user.full_name == "Worker"
    assert item.session_name == "Show A"
    response = EventSessionStaffRead.model_validate(item)
    assert response.user.full_name == "Worker" and response.session_name == "Show A"
    assert response.shift_start == datetime(2026, 8, 10, 10)
    assert EventSessionStaffCreate(event_staff_id=staff["supervisor"].id).shift_start is None
    with pytest.raises(ValueError, match="shift_start must be before shift_end"):
        EventSessionStaffCreate(event_staff_id=staff["supervisor"].id, shift_start="2026-08-10T13:00:00Z", shift_end="2026-08-10T12:00:00Z")
    with pytest.raises(ValueError):
        EventSessionStaffCreate(event_staff_id=staff["supervisor"].id, shift_start="not-a-date")


def test_general_and_show_tasks_filters_and_safe_reassignment(context):
    db, events, users, _, shows = context
    general = task_service.create_task(db, events[0].id, TaskCreate(title="General", priority="MEDIUM"), users["admin"])
    specific = task_service.create_task(db, events[0].id, TaskCreate(title="Show", priority="HIGH", session_id=shows[0].id), users["admin"])
    assert general.session_id is None and specific.session_id == shows[0].id
    items, total = task_service.list_event_tasks(db, event_id=events[0].id, current_user=users["admin"], status_filter=None, assigned_to=None, page=1, limit=20, session_id=shows[0].id, scope="general_and_session")
    assert total == 2 and {item.id for item in items} == {general.id, specific.id}
    moved = task_service.update_task(db, specific.id, TaskUpdate(session_id=shows[1].id, reassignment_reason="Schedule correction"), users["admin"])
    assert moved.session_id == shows[1].id
    db.add(Evidence(event_id=events[0].id, task_id=moved.id, uploaded_by=users["admin"].id, file_url="private/evidences/test.webp", file_type="image/webp"))
    db.commit()
    with pytest.raises(HTTPException, match="cannot be reassigned"):
        task_service.update_task(db, moved.id, TaskUpdate(session_id=shows[0].id, reassignment_reason="Wrong"), users["admin"])


def test_incident_inherits_task_show_and_corrective_task_inherits_incident(context):
    db, events, users, _, shows = context
    source = task_service.create_task(db, events[0].id, TaskCreate(title="Inspect", priority="MEDIUM", session_id=shows[0].id), users["admin"])
    incident = incident_service.create_incident(db, events[0].id, IncidentCreate(title="Failure", description="Operational failure", source_task_id=source.id), users["supervisor"])
    assert incident.session_id == shows[0].id
    with pytest.raises(HTTPException, match="contradicts"):
        incident_service.create_incident(db, events[0].id, IncidentCreate(title="Bad", description="Bad relation", source_task_id=source.id, session_id=shows[1].id), users["supervisor"])
    corrective = incident_service.create_corrective_task(db, incident.id, IncidentCorrectiveTaskCreate(title="Correct", priority="HIGH"), users["admin"])
    assert corrective.session_id == incident.session_id and corrective.source_incident_id == incident.id
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Task(event_id=incident.event_id, title="Duplicate corrective", source_incident_id=incident.id))
        db.flush()
    with pytest.raises(HTTPException, match="inherited"):
        incident_service.update_incident(db, incident.id, IncidentUpdate(session_id=shows[1].id, reassignment_reason="No"), users["admin"])


def test_cross_event_session_rejected_and_historical_null_semantics(context):
    db, events, users, staff, shows = context
    with pytest.raises(HTTPException, match="does not belong"):
        task_service.create_task(db, events[0].id, TaskCreate(title="Bad", priority="LOW", session_id=shows[2].id), users["admin"])
    other_task = task_service.create_task(db, events[1].id, TaskCreate(title="Other event task"), users["admin"])
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Evidence(event_id=events[0].id, task_id=other_task.id, file_url="private/evidences/cross.webp"))
        db.flush()
    historical_task = Task(event_id=events[0].id, title="Historical")
    historical_incident = Incident(event_id=events[0].id, title="Historical incident", description="Legacy")
    db.add_all([historical_task, historical_incident])
    db.commit()
    assert historical_task.session_id is None and historical_incident.session_id is None
    with pytest.raises(HTTPException, match="internal"):
        event_session_staff_service.operational_summary(db, shows[0].id, users["client"])
    with pytest.raises(HTTPException, match="internal"):
        event_session_staff_service.list_person_sessions(db, staff["worker"].id, users["client"])


def test_direct_task_uuid_respects_internal_role_boundary(context):
    db, events, users, _, _ = context
    task = task_service.create_task(db, events[0].id, TaskCreate(title="Private task"), users["admin"])
    for role in ("client", "logistics"):
        with pytest.raises(HTTPException, match="not authorized"):
            task_service.get_task(db, task.id, users[role])


def test_evidence_show_is_derived_without_exposing_storage_key(context, monkeypatch):
    db, events, users, _, shows = context
    task = task_service.create_task(db, events[0].id, TaskCreate(title="Evidence task", priority="MEDIUM", session_id=shows[0].id), users["admin"])
    monkeypatch.setattr(evidence_service, "save_evidence_file", lambda _: ("private/evidences/test.webp", "image/webp"))
    evidence = evidence_service.create_evidence(db, event_id=events[0].id, task_id=task.id, incident_id=None, description="Derived", file=UploadFile(filename="test.webp", file=BytesIO(b"x")), current_user=users["admin"])
    assert evidence.session_id == shows[0].id
    assert evidence.session_name == "Show A"
    response = EvidenceRead.model_validate(evidence)
    assert response.session_id == shows[0].id and response.session_name == "Show A"
    assert response.file_url == f"/evidences/{evidence.id}/download"
    items, total = evidence_service.list_event_evidences(db, event_id=events[0].id, current_user=users["admin"], page=1, limit=20, session_id=shows[0].id)
    assert total == 1 and items[0].session_id == shows[0].id and items[0].session_name == "Show A"
    with pytest.raises(HTTPException, match="contradicts"):
        evidence_service.create_evidence(db, event_id=events[0].id, task_id=task.id, incident_id=None, session_id=shows[1].id, description="Bad", file=UploadFile(filename="test.webp", file=BytesIO(b"x")), current_user=users["admin"])
    shows[1].archived_at = datetime(2026, 8, 9)
    db.commit()
    with pytest.raises(HTTPException, match="Archived"):
        evidence_service.create_evidence(db, event_id=events[0].id, task_id=None, incident_id=None, session_id=shows[1].id, description="Archived", file=UploadFile(filename="test.webp", file=BytesIO(b"x")), current_user=users["admin"])


def _rls(engine, user, sql, params=None):
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("select set_config('app.current_user_id', :value, true)"), {"value": str(user.id)})
            connection.execute(text("select set_config('app.current_role', :value, true)"), {"value": user.role.value})
            connection.execute(text("select set_config('app.current_client_id', :value, true)"), {"value": str(user.client_id or "")})
            result = connection.execute(text(sql), params or {})
            effective = bool(result.fetchall()) if result.returns_rows else result.rowcount > 0
            transaction.rollback()
            return effective
        except DBAPIError:
            transaction.rollback()
            return False


@pytest.mark.parametrize("role_name,can_read,can_write", [
    ("superadmin", True, True), ("admin", True, True), ("supervisor", True, True),
    ("worker", True, False), ("logistics", False, False), ("client", False, False),
    ("other", False, False),
])
def test_show_staff_rls_matrix(context, role_name, can_read, can_write):
    runtime_url = os.environ.get("RLS_DATABASE_URL")
    if not runtime_url:
        pytest.fail("RLS_DATABASE_URL is required")
    db, _, users, staff, shows = context
    item = event_session_staff_service.create_assignment(db, shows[0].id, EventSessionStaffCreate(event_staff_id=staff["worker"].id), users["admin"])
    engine = create_engine(runtime_url)
    try:
        read = _rls(engine, users[role_name], "select id from event_session_staff where id=:id", {"id": item.id})
        write = _rls(engine, users[role_name], "update event_session_staff set operational_role=operational_role where id=:id", {"id": item.id})
        assert (read, write) == (can_read, can_write)
    finally:
        engine.dispose()


@pytest.mark.parametrize("role_name,task_access,incident_access,evidence_access", [
    ("superadmin", (True, True), (True, True), (True, True)),
    ("admin", (True, True), (True, True), (True, True)),
    ("supervisor", (True, True), (True, True), (True, True)),
    ("worker", (True, True), (True, False), (True, True)),
    ("logistics", (False, False), (False, False), (True, False)),
    ("client", (False, False), (False, False), (True, False)),
    ("other", (False, False), (False, False), (False, False)),
])
def test_operational_entities_rls_matrix(
    context, role_name, task_access, incident_access, evidence_access
):
    runtime_url = os.environ.get("RLS_DATABASE_URL")
    if not runtime_url:
        pytest.fail("RLS_DATABASE_URL is required")
    db, events, users, _, shows = context
    task = task_service.create_task(
        db,
        events[0].id,
        TaskCreate(title="RLS task", assigned_to=users["worker"].id, session_id=shows[0].id),
        users["admin"],
    )
    incident = Incident(
        event_id=events[0].id,
        title="RLS incident",
        description="RLS incident",
        session_id=shows[0].id,
        reported_by=users["worker"].id,
    )
    evidence = Evidence(
        event_id=events[0].id,
        session_id=shows[0].id,
        uploaded_by=users["worker"].id,
        file_url="private/evidences/rls.webp",
        file_type="image/webp",
    )
    db.add_all([incident, evidence])
    db.commit()
    engine = create_engine(runtime_url)
    try:
        actual = []
        for table, item in (("tasks", task), ("incidents", incident), ("evidences", evidence)):
            actual.append((
                _rls(engine, users[role_name], f"select id from {table} where id=:id", {"id": item.id}),
                _rls(engine, users[role_name], f"update {table} set event_id=event_id where id=:id", {"id": item.id}),
            ))
        assert actual == [task_access, incident_access, evidence_access]
    finally:
        engine.dispose()
