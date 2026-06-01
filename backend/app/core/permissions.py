from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Event, EventStaff, Task, User
from app.models.enums import UserRole


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


def can_access_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True

    event = db.get(Event, event_id)
    if event is None:
        return False

    if user.role == UserRole.CLIENT:
        return user.client_id is not None and event.client_id == user.client_id
    if user.role == UserRole.SUPERVISOR:
        return _is_assigned_to_event(user, event_id, db)
    if user.role == UserRole.WORKER:
        return _is_assigned_to_event(user, event_id, db) or _has_task_in_event(user, event_id, db)
    return False


def can_manage_event(user: User, event_id: UUID, db: Session) -> bool:
    if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        return True
    if user.role == UserRole.SUPERVISOR:
        return _is_assigned_to_event(user, event_id, db)
    return False

