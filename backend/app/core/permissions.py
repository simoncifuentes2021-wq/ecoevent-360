from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Event, EventStaff, Task, User
from app.models.enums import EventStatus, UserRole

CLOSURE_WINDOW_DAYS = 7
OPERATIONAL_ROLES = {UserRole.SUPERVISOR, UserRole.WORKER}


def can_access_client(user: User, client_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.CLIENT:
        return user.client_id == client_id
    return False


def _is_assigned_to_event(user: User, event_id: UUID, db: Session) -> bool:
    return db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user.id)
    ) is not None


def _has_task_in_event(user: User, event_id: UUID, db: Session) -> bool:
    return db.scalar(
        select(Task.id).where(Task.event_id == event_id, Task.assigned_to == user.id)
    ) is not None


def _has_operational_relation(user: User, event_id: UUID, db: Session) -> bool:
    return _is_assigned_to_event(user, event_id, db) or _has_task_in_event(user, event_id, db)


def _is_in_closure_window(event: Event) -> bool:
    return datetime.utcnow() <= event.end_date + timedelta(days=CLOSURE_WINDOW_DAYS)


def is_hidden_from_operational_roles(event: Event, user: User) -> bool:
    return user.role in OPERATIONAL_ROLES and event.hidden_from_operations


def can_view_operational_event(user: User, event: Event, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.CLIENT:
        return user.client_id is not None and event.client_id == user.client_id
    if user.role in OPERATIONAL_ROLES:
        if is_hidden_from_operational_roles(event, user):
            return False
        if event.status == EventStatus.QUOTE:
            return False
        return _has_operational_relation(user, event.id, db)
    return False


def can_operate_event(user: User, event_id: UUID, db: Session) -> bool:
    event = db.get(Event, event_id)
    if event is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status in {EventStatus.PLANNING, EventStatus.IN_PROGRESS} or (
            event.status == EventStatus.FINISHED and _is_in_closure_window(event)
        )
    if user.role == UserRole.WORKER:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status == EventStatus.IN_PROGRESS
    return False


def can_close_assigned_task(user: User, event_id: UUID, db: Session) -> bool:
    event = db.get(Event, event_id)
    if event is None:
        return False
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role in OPERATIONAL_ROLES:
        if not can_view_operational_event(user, event, db):
            return False
        return event.status == EventStatus.IN_PROGRESS or (
            event.status == EventStatus.FINISHED and _is_in_closure_window(event)
        )
    return False


def can_access_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True

    event = db.get(Event, event_id)
    if event is None:
        return False

    return can_view_operational_event(user, event, db)


def can_manage_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return can_operate_event(user, event_id, db)
    return False
