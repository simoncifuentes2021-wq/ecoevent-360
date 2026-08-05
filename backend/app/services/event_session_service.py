from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import (
    BikeZoneRecord,
    Event,
    EventForm,
    EventSession,
    EventStaff,
    FormQRCode,
    FormResponse,
    User,
)
from app.models.enums import EventSessionStatus, UserRole
from app.schemas.event_form_schema import EventSessionCreate, EventSessionUpdate


TRANSITIONS = {
    EventSessionStatus.PLANNED: {EventSessionStatus.READY, EventSessionStatus.CANCELLED},
    EventSessionStatus.READY: {EventSessionStatus.PLANNED, EventSessionStatus.IN_PROGRESS, EventSessionStatus.CANCELLED},
    EventSessionStatus.IN_PROGRESS: {EventSessionStatus.COMPLETED, EventSessionStatus.CANCELLED},
    EventSessionStatus.COMPLETED: set(),
    EventSessionStatus.CANCELLED: {EventSessionStatus.PLANNED},
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_can_view(db: Session, event_id: UUID, user: User) -> Event:
    event = _event_or_404(db, event_id)
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _ensure_can_manage(db: Session, event_id: UUID, user: User) -> Event:
    event = _event_or_404(db, event_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def get_session_or_404(db: Session, session_id: UUID) -> EventSession:
    session = db.get(EventSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def ensure_session_belongs_to_event(
    db: Session, session_id: UUID | None, event_id: UUID, *, allow_archived: bool = False
) -> None:
    if not session_id:
        return
    session = get_session_or_404(db, session_id)
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id does not belong to event")
    if session.archived_at and not allow_archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is archived")


def _validate_payload(db: Session, event: Event, data: dict, current: EventSession | None = None) -> None:
    session_date = data.get("session_date", current.session_date if current else None)
    start_time = data.get("start_time", current.start_time if current else None)
    end_time = data.get("end_time", current.end_time if current else None)
    responsible_id = data.get("responsible_id", current.responsible_id if current else None)
    if session_date and not (event.start_date.date() <= session_date <= event.end_date.date()):
        raise HTTPException(status_code=422, detail="Session date must be within the event date range")
    if start_time and end_time and end_time <= start_time:
        raise HTTPException(status_code=422, detail="Session end time must be after start time")
    if responsible_id and not db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event.id, EventStaff.user_id == responsible_id)
    ):
        raise HTTPException(status_code=422, detail="Responsible user must be assigned to the event")


def _has_overlap(db: Session, item: EventSession) -> bool:
    if not item.session_date or not item.start_time or not item.end_time:
        return False
    scope = []
    if item.stage_name:
        scope.append(EventSession.stage_name == item.stage_name)
    elif item.venue_name:
        scope.append(EventSession.venue_name == item.venue_name)
    else:
        return False
    return db.scalar(
        select(EventSession.id).where(
            EventSession.event_id == item.event_id,
            EventSession.id != item.id,
            EventSession.archived_at.is_(None),
            EventSession.session_date == item.session_date,
            EventSession.start_time < item.end_time,
            EventSession.end_time > item.start_time,
            *scope,
        ).limit(1)
    ) is not None


def _decorate(db: Session, item: EventSession) -> EventSession:
    item.overlap_warning = _has_overlap(db, item)
    return item


def _for_viewer(db: Session, item: EventSession, user: User) -> EventSession | dict:
    item = _decorate(db, item)
    if user.role != UserRole.CLIENT:
        return item
    # Internal notes are operational data and never belong in the client portal/API response.
    return {column.name: getattr(item, column.name) for column in EventSession.__table__.columns if column.name != "internal_notes"} | {
        "overlap_warning": item.overlap_warning,
        "internal_notes": None,
    }


def create_session(db: Session, event_id: UUID, payload: EventSessionCreate, user: User) -> EventSession:
    event = _ensure_can_manage(db, event_id, user)
    data = payload.model_dump()
    _validate_payload(db, event, data)
    session = EventSession(event_id=event_id, **data)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _decorate(db, session)


def list_event_sessions(
    db: Session, event_id: UUID, user: User, *, include_archived: bool = False
) -> list[EventSession | dict]:
    _ensure_can_view(db, event_id, user)
    query = select(EventSession).where(EventSession.event_id == event_id)
    if not include_archived:
        query = query.where(EventSession.archived_at.is_(None))
    items = list(db.scalars(query.order_by(EventSession.sort_order, EventSession.session_date.asc().nulls_last(), EventSession.start_time.asc().nulls_last())).all())
    return [_for_viewer(db, item, user) for item in items]


def get_session(db: Session, session_id: UUID, user: User) -> EventSession | dict:
    session = get_session_or_404(db, session_id)
    _ensure_can_view(db, session.event_id, user)
    return _for_viewer(db, session, user)


def update_session(db: Session, session_id: UUID, payload: EventSessionUpdate, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    event = _ensure_can_manage(db, session.event_id, user)
    if session.archived_at:
        raise HTTPException(status_code=409, detail="Archived sessions cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    _validate_payload(db, event, data, session)
    for field, value in data.items():
        setattr(session, field, value)
    session.updated_at = _utcnow()
    db.commit()
    db.refresh(session)
    return _decorate(db, session)


def transition_session(db: Session, session_id: UUID, target: EventSessionStatus, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    if session.archived_at:
        raise HTTPException(status_code=409, detail="Archived sessions cannot change status")
    if target == session.status:
        return _decorate(db, session)
    if target not in TRANSITIONS[session.status]:
        raise HTTPException(status_code=409, detail=f"Invalid transition from {session.status} to {target}")
    session.status = target
    session.updated_at = _utcnow()
    db.commit()
    db.refresh(session)
    return _decorate(db, session)


def archive_session(db: Session, session_id: UUID, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    session.archived_at = session.archived_at or _utcnow()
    session.updated_at = _utcnow()
    db.commit()
    db.refresh(session)
    return _decorate(db, session)


def restore_session(db: Session, session_id: UUID, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    session.archived_at = None
    session.updated_at = _utcnow()
    db.commit()
    db.refresh(session)
    return _decorate(db, session)


def duplicate_session(db: Session, session_id: UUID, user: User) -> EventSession:
    source = get_session_or_404(db, session_id)
    _ensure_can_manage(db, source.event_id, user)
    clone = EventSession(
        event_id=source.event_id, name=f"{source.name} (copia)", description=source.description,
        session_date=source.session_date, start_time=source.start_time, end_time=source.end_time,
        venue_name=source.venue_name, stage_name=source.stage_name,
        expected_attendees=source.expected_attendees, real_attendees=None,
        responsible_id=source.responsible_id, status=EventSessionStatus.PLANNED,
        sort_order=source.sort_order + 1, internal_notes=source.internal_notes,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return _decorate(db, clone)


def reorder_sessions(db: Session, event_id: UUID, session_ids: list[UUID], user: User) -> list[EventSession]:
    _ensure_can_manage(db, event_id, user)
    if len(session_ids) != len(set(session_ids)):
        raise HTTPException(status_code=422, detail="session_ids contains duplicates")
    items = list(db.scalars(select(EventSession).where(EventSession.event_id == event_id, EventSession.archived_at.is_(None))).all())
    if {item.id for item in items} != set(session_ids):
        raise HTTPException(status_code=422, detail="session_ids must contain every active session in the event")
    by_id = {item.id: item for item in items}
    for order, session_id in enumerate(session_ids):
        by_id[session_id].sort_order = order
    db.commit()
    return [_decorate(db, by_id[item_id]) for item_id in session_ids]


def delete_session(db: Session, session_id: UUID, user: User) -> None:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    dependencies = sum(db.scalar(select(func.count()).select_from(model).where(model.session_id == session.id)) or 0 for model in (EventForm, FormResponse, BikeZoneRecord, FormQRCode))
    if dependencies:
        raise HTTPException(status_code=409, detail="Session has associated data and must be archived")
    db.delete(session)
    db.commit()
