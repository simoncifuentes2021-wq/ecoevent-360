from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Event, EventSession, User
from app.models.enums import UserRole
from app.schemas.event_form_schema import EventSessionCreate, EventSessionUpdate


def _event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_can_view(db: Session, event_id: UUID, user: User) -> None:
    _event_or_404(db, event_id)
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage(db: Session, event_id: UUID, user: User) -> None:
    _event_or_404(db, event_id)
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def get_session_or_404(db: Session, session_id: UUID) -> EventSession:
    session = db.get(EventSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def ensure_session_belongs_to_event(db: Session, session_id: UUID | None, event_id: UUID) -> None:
    if not session_id:
        return
    session = get_session_or_404(db, session_id)
    if session.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="session_id does not belong to event")


def create_session(db: Session, event_id: UUID, payload: EventSessionCreate, user: User) -> EventSession:
    _ensure_can_manage(db, event_id, user)
    session = EventSession(event_id=event_id, **payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_event_sessions(db: Session, event_id: UUID, user: User) -> list[EventSession]:
    _ensure_can_view(db, event_id, user)
    return list(
        db.scalars(
            select(EventSession)
            .where(EventSession.event_id == event_id)
            .order_by(EventSession.session_date.asc().nulls_last(), EventSession.start_time.asc().nulls_last(), EventSession.created_at.desc())
        ).all()
    )


def get_session(db: Session, session_id: UUID, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    _ensure_can_view(db, session.event_id, user)
    return session


def update_session(db: Session, session_id: UUID, payload: EventSessionUpdate, user: User) -> EventSession:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, session_id: UUID, user: User) -> None:
    session = get_session_or_404(db, session_id)
    _ensure_can_manage(db, session.event_id, user)
    db.delete(session)
    db.commit()
