from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Event, EventStaff, Task, User
from app.models.enums import TaskStatus, UserRole
from app.schemas.staff_schema import EventStaffCreate

ASSIGNABLE_ROLES = {UserRole.SUPERVISOR, UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}
ACTIVE_TASK_STATUSES = {TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OBSERVED}


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def assign_staff(
    db: Session, event_id: UUID, payload: EventStaffCreate, current_user: User
) -> EventStaff:
    _get_event_or_404(db, event_id)
    if not can_manage_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive")
    if user.role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SUPERVISOR, WORKER or LOGISTICS_OPERATOR users can be assigned to events",
        )

    existing = db.scalar(
        select(EventStaff.id).where(
            EventStaff.event_id == event_id, EventStaff.user_id == payload.user_id
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this event",
        )

    staff = EventStaff(event_id=event_id, **payload.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def list_event_staff(db: Session, event_id: UUID, current_user: User) -> list[EventStaff]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return list(
        db.scalars(
            select(EventStaff)
            .options(selectinload(EventStaff.user))
            .where(EventStaff.event_id == event_id)
            .order_by(EventStaff.created_at)
        ).all()
    )


def remove_staff(db: Session, event_id: UUID, user_id: UUID, current_user: User) -> None:
    _get_event_or_404(db, event_id)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    staff = db.scalar(
        select(EventStaff).where(EventStaff.event_id == event_id, EventStaff.user_id == user_id)
    )
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff assignment not found")

    active_task = db.scalar(
        select(Task.id)
        .where(
            Task.event_id == event_id,
            Task.assigned_to == user_id,
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .limit(1)
    )
    if active_task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove staff with active tasks assigned",
        )

    db.delete(staff)
    db.commit()
