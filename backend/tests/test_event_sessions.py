from datetime import date, datetime, time, timedelta
import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.core import (
    BikeZoneRecord, Client, Event, EventForm, EventSession, EventStaff,
    FormQRCode, FormResponse, User,
)
from app.models.enums import EventFormStatus, EventFormType, EventSessionStatus, EventStatus, UserRole
from app.schemas.event_form_schema import EventSessionCreate, EventSessionUpdate
from app.services import event_session_service
from app.api.routers import event_forms as event_forms_router


@pytest.fixture()
def session_context():
    db = SessionLocal()
    suffix = uuid4().hex[:10]
    client = Client(business_name=f"Session Client {suffix}")
    other_client = Client(business_name=f"Other Session Client {suffix}")
    db.add_all([client, other_client]); db.flush()
    users = {
        name: User(full_name=name, email=f"session-{name}-{suffix}@example.test", password_hash="x", role=role,
                   client_id=client.id if name == "client" else None)
        for name, role in {
            "admin": UserRole.ADMIN, "superadmin": UserRole.SUPER_ADMIN,
            "supervisor": UserRole.SUPERVISOR, "other_supervisor": UserRole.SUPERVISOR,
            "worker": UserRole.WORKER, "logistics": UserRole.LOGISTICS_OPERATOR,
            "client": UserRole.CLIENT,
        }.items()
    }
    db.add_all(users.values()); db.flush()
    start = datetime(2026, 8, 1, 9)
    event = Event(client_id=client.id, name=f"Session Event {suffix}", start_date=start,
                  end_date=start + timedelta(days=3), status=EventStatus.PLANNING, created_by=users["admin"].id)
    other_event = Event(client_id=other_client.id, name=f"Other Session Event {suffix}", start_date=start,
                        end_date=start + timedelta(days=3), status=EventStatus.PLANNING, created_by=users["admin"].id)
    db.add_all([event, other_event]); db.flush()
    db.add_all([EventStaff(event_id=event.id, user_id=users[name].id) for name in ("supervisor", "worker", "logistics")]
               + [EventStaff(event_id=other_event.id, user_id=users["other_supervisor"].id)])
    db.commit()
    try:
        yield db, event, other_event, users
    finally:
        db.rollback()
        db.execute(delete(AuditLog).where(AuditLog.event_id.in_([event.id, other_event.id])))
        db.execute(delete(Event).where(Event.id.in_([event.id, other_event.id])))
        db.execute(delete(User).where(User.id.in_([user.id for user in users.values()])))
        db.execute(delete(Client).where(Client.id.in_([client.id, other_client.id])))
        db.commit(); db.close()


def _payload(name="Show", **values):
    data = {"name": name, "session_date": date(2026, 8, 2), "start_time": time(10), "end_time": time(11)}
    data.update(values)
    return EventSessionCreate(**data)


def test_old_and_new_payloads_and_responsible_validation(session_context):
    db, event, _, users = session_context
    old = event_session_service.create_session(db, event.id, EventSessionCreate(name="Legacy payload"), users["admin"])
    assert old.status == EventSessionStatus.PLANNED and old.responsible_id is None and old.sort_order == 0
    new = event_session_service.create_session(db, event.id, _payload("Complete", responsible_id=users["worker"].id,
        expected_attendees=100, real_attendees=80, internal_notes="private", sort_order=2), users["admin"])
    assert (new.responsible_id, new.real_attendees, new.internal_notes) == (users["worker"].id, 80, "private")
    with pytest.raises(HTTPException, match="assigned to the event"):
        event_session_service.create_session(db, event.id, _payload("Bad responsible", responsible_id=users["other_supervisor"].id), users["admin"])


@pytest.mark.parametrize("values,message", [
    ({"session_date": date(2026, 8, 5)}, "within the event"),
    ({"start_time": time(12), "end_time": time(11)}, "after start"),
])
def test_date_and_time_validation(session_context, values, message):
    db, event, _, users = session_context
    with pytest.raises(HTTPException, match=message):
        event_session_service.create_session(db, event.id, EventSessionCreate(name="Invalid", **values), users["admin"])


def test_overlap_by_stage_and_fallback_venue(session_context):
    db, event, _, users = session_context
    event_session_service.create_session(db, event.id, _payload("Stage 1", stage_name="Main", venue_name="A"), users["admin"])
    stage = event_session_service.create_session(db, event.id, _payload("Stage 2", stage_name="Main", venue_name="B", start_time=time(10, 30), end_time=time(11, 30)), users["admin"])
    assert stage.overlap_warning is True
    event_session_service.create_session(db, event.id, _payload("Venue 1", venue_name="C", start_time=time(12), end_time=time(13)), users["admin"])
    venue = event_session_service.create_session(db, event.id, _payload("Venue 2", venue_name="C", start_time=time(12, 30), end_time=time(13, 30)), users["admin"])
    assert venue.overlap_warning is True


def test_transitions_duplicate_archive_restore_and_filters(session_context):
    db, event, _, users = session_context
    item = event_session_service.create_session(db, event.id, _payload(real_attendees=75), users["admin"])
    assert event_session_service.transition_session(db, item.id, EventSessionStatus.READY, users["admin"]).status == EventSessionStatus.READY
    with pytest.raises(HTTPException, match="Invalid transition"):
        event_session_service.transition_session(db, item.id, EventSessionStatus.COMPLETED, users["admin"])
    clone = event_session_service.duplicate_session(db, item.id, users["admin"])
    assert clone.real_attendees is None and clone.status == EventSessionStatus.PLANNED
    event_session_service.archive_session(db, item.id, users["admin"])
    assert item.id not in {value.id for value in event_session_service.list_event_sessions(db, event.id, users["admin"])}
    assert item.id in {value.id for value in event_session_service.list_event_sessions(db, event.id, users["admin"], include_archived=True)}
    assert event_session_service.restore_session(db, item.id, users["admin"]).archived_at is None


def test_reorder_and_conflicts(session_context):
    db, event, _, users = session_context
    items = [event_session_service.create_session(db, event.id, _payload(str(index), start_time=time(10 + index), end_time=time(11 + index)), users["admin"]) for index in range(3)]
    ordered = event_session_service.reorder_sessions(db, event.id, [items[2].id, items[0].id, items[1].id], users["admin"])
    assert [(item.id, item.sort_order) for item in ordered] == [(items[2].id, 0), (items[0].id, 1), (items[1].id, 2)]
    with pytest.raises(HTTPException, match="duplicates"):
        event_session_service.reorder_sessions(db, event.id, [items[0].id] * 3, users["admin"])
    with pytest.raises(HTTPException, match="every active"):
        event_session_service.reorder_sessions(db, event.id, [items[0].id], users["admin"])


def _form(db, event, session_id=None):
    item = EventForm(event_id=event.id, session_id=session_id, title=f"Form {uuid4().hex}", form_type=EventFormType.CUSTOM,
                     public_slug=f"form-{uuid4().hex}", status=EventFormStatus.DRAFT)
    db.add(item); db.flush(); return item


@pytest.mark.parametrize("relation", ["form", "response", "bike", "qr"])
def test_delete_blocked_by_each_relation(session_context, relation):
    db, event, _, users = session_context
    target = event_session_service.create_session(db, event.id, _payload(f"Delete {relation}"), users["admin"])
    form = _form(db, event, target.id if relation == "form" else None)
    if relation in {"response", "bike"}:
        response = FormResponse(form_id=form.id, event_id=event.id, session_id=target.id if relation == "response" else None, raw_data={})
        db.add(response); db.flush()
        if relation == "bike": db.add(BikeZoneRecord(response_id=response.id, event_id=event.id, session_id=target.id, code=f"B-{uuid4().hex}"))
    if relation == "qr": db.add(FormQRCode(form_id=form.id, event_id=event.id, session_id=target.id, label="QR", target_url="https://example.test"))
    db.commit()
    with pytest.raises(HTTPException, match="must be archived"):
        event_session_service.delete_session(db, target.id, users["admin"])


def test_delete_empty_session_and_client_notes_and_cross_event_access(session_context):
    db, event, other_event, users = session_context
    empty = event_session_service.create_session(db, event.id, _payload("Empty"), users["admin"])
    event_session_service.delete_session(db, empty.id, users["admin"])
    assert db.get(EventSession, empty.id) is None
    private = event_session_service.create_session(db, event.id, _payload("Private", internal_notes="never-client"), users["admin"])
    client_view = event_session_service.get_session(db, private.id, users["client"])
    assert isinstance(client_view, dict) and client_view["internal_notes"] is None
    foreign = event_session_service.create_session(db, other_event.id, _payload("Foreign"), users["admin"])
    with pytest.raises(HTTPException) as error:
        event_session_service.get_session(db, foreign.id, users["supervisor"])
    assert error.value.status_code == 403


def _rls_run(engine, user, sql, params=None):
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("select set_config('app.current_user_id',:v,true)"), {"v": str(user.id)})
        connection.execute(text("select set_config('app.current_role',:v,true)"), {"v": user.role.value})
        connection.execute(text("select set_config('app.current_client_id',:v,true)"), {"v": str(user.client_id or "")})
        try:
            result = connection.execute(text(sql), params or {})
            rows = result.fetchall() if result.returns_rows else []
            effective = bool(rows) if result.returns_rows else result.rowcount > 0
            transaction.rollback(); return effective, None
        except DBAPIError as error:
            transaction.rollback(); return False, error


@pytest.mark.parametrize("role_name,can_read,can_write", [
    ("admin", True, True), ("superadmin", True, True), ("supervisor", True, True),
    ("other_supervisor", False, False), ("worker", True, False),
    ("logistics", True, False), ("client", True, False),
])
def test_event_session_rls_by_role(session_context, role_name, can_read, can_write):
    runtime_url = os.environ.get("RLS_DATABASE_URL")
    if not runtime_url: pytest.fail("RLS_DATABASE_URL is required")
    db, event, _, users = session_context
    item = event_session_service.create_session(db, event.id, _payload("RLS"), users["admin"])
    engine = create_engine(runtime_url)
    try:
        read, _ = _rls_run(engine, users[role_name], "select id from event_sessions where id=:id", {"id": item.id})
        inserted, _ = _rls_run(engine, users[role_name], "insert into event_sessions(id,event_id,name) values (:id,:event,'RLS inserted')", {"id": uuid4(), "event": event.id})
        updated, _ = _rls_run(engine, users[role_name], "update event_sessions set name=name where id=:id", {"id": item.id})
        deleted, _ = _rls_run(engine, users[role_name], "delete from event_sessions where id=:id", {"id": item.id})
        assert (read, inserted, updated, deleted) == (can_read, can_write, can_write, can_write)
    finally: engine.dispose()


def test_all_session_mutations_are_audited(session_context):
    db, event, _, users = session_context
    request = Request({
        "type": "http", "method": "POST", "path": "/api/v1/event-sessions",
        "query_string": b"", "scheme": "http", "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234), "headers": [],
    })
    admin = users["admin"]
    item = event_forms_router.create_session(event.id, _payload("Audited"), request, db, admin)
    event_forms_router.update_session(item.id, EventSessionUpdate(description="updated"), request, db, admin)
    event_forms_router.transition_session(
        item.id,
        event_forms_router.EventSessionTransition(status=EventSessionStatus.READY),
        request, db, admin,
    )
    clone = event_forms_router.duplicate_session(item.id, request, db, admin)
    event_forms_router.reorder_sessions(
        event.id,
        event_forms_router.EventSessionReorder(session_ids=[clone.id, item.id]),
        request, db, admin,
    )
    event_forms_router.archive_session(item.id, request, db, admin)
    event_forms_router.restore_session(item.id, request, db, admin)
    disposable = event_forms_router.create_session(event.id, _payload("Disposable", start_time=time(14), end_time=time(15)), request, db, admin)
    event_forms_router.delete_session(disposable.id, request, db, admin)
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.event_id == event.id)).all())
    assert {
        "SESSION_CREATED", "SESSION_UPDATED", "SESSION_STATUS_CHANGED", "SESSION_DUPLICATED",
        "SESSIONS_REORDERED", "SESSION_ARCHIVED", "SESSION_RESTORED", "SESSION_DELETED",
    } <= actions
