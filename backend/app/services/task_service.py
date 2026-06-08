from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_close_assigned_task, can_manage_event, can_operate_event
from app.models.core import Event, EventStaff, EventZone, Task, User
from app.models.enums import EventStatus, TaskStatus, UserRole
from app.schemas.task_schema import TaskComplete, TaskCreate, TaskStatusUpdate, TaskUpdate

ASSIGNEE_ROLES = {UserRole.SUPERVISOR, UserRole.WORKER}


def get_task_or_404(db: Session, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _validate_zone(db: Session, event_id: UUID, zone_id: UUID | None) -> None:
    if zone_id is None:
        return
    zone = db.get(EventZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    if zone.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone does not belong to this event",
        )


def _validate_assignee(db: Session, event_id: UUID, user_id: UUID | None) -> None:
    if user_id is None:
        return
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee is inactive")
    if user.role not in ASSIGNEE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be WORKER or SUPERVISOR",
        )
    assigned = db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user_id)
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be assigned to the event staff",
        )


def _ensure_can_view_task(task: Task, current_user: User, db: Session) -> None:
    if current_user.role == UserRole.WORKER:
        if task.assigned_to != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return
    if not can_access_event(current_user, task.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _ensure_can_manage_task(task: Task, current_user: User, db: Session) -> None:
    if not can_manage_event(current_user, task.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def create_task(db: Session, event_id: UUID, payload: TaskCreate, current_user: User) -> Task:
    _get_event_or_404(db, event_id)
    if not can_manage_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _validate_zone(db, event_id, payload.zone_id)
    _validate_assignee(db, event_id, payload.assigned_to)

    task = Task(
        event_id=event_id,
        created_by=current_user.id,
        status=TaskStatus.PENDING,
        **payload.model_dump(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_event_tasks(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    status_filter: TaskStatus | None,
    assigned_to: UUID | None,
    page: int,
    limit: int,
) -> tuple[list[Task], int]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [Task.event_id == event_id]
    if current_user.role == UserRole.WORKER:
        filters.append(Task.assigned_to == current_user.id)
    elif assigned_to is not None:
        filters.append(Task.assigned_to == assigned_to)
    if status_filter is not None:
        filters.append(Task.status == status_filter)

    total = db.scalar(select(func.count()).select_from(Task).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Task)
            .where(*filters)
            .order_by(Task.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_task(db: Session, task_id: UUID, current_user: User) -> Task:
    task = get_task_or_404(db, task_id)
    _ensure_can_view_task(task, current_user, db)
    return task


def update_task(db: Session, task_id: UUID, payload: TaskUpdate, current_user: User) -> Task:
    task = get_task_or_404(db, task_id)
    _ensure_can_manage_task(task, current_user, db)
    data = payload.model_dump(exclude_unset=True)
    if "zone_id" in data:
        _validate_zone(db, task.event_id, data["zone_id"])
    if "assigned_to" in data:
        _validate_assignee(db, task.event_id, data["assigned_to"])

    for field, value in data.items():
        setattr(task, field, value)
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task_status(
    db: Session, task_id: UUID, payload: TaskStatusUpdate, current_user: User
) -> Task:
    task = get_task_or_404(db, task_id)
    new_status = payload.status

    if current_user.role == UserRole.WORKER:
        if task.assigned_to != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        if not can_operate_event(current_user, task.event_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Event is not open for operational updates",
            )
        allowed = {
            (TaskStatus.PENDING, TaskStatus.IN_PROGRESS),
            (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
        }
        if (task.status, new_status) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status transition for WORKER",
            )
    elif current_user.role == UserRole.SUPERVISOR:
        if not can_manage_event(current_user, task.event_id, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        allowed = {
            (TaskStatus.PENDING, TaskStatus.IN_PROGRESS),
            (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED),
            (TaskStatus.PENDING, TaskStatus.OBSERVED),
            (TaskStatus.IN_PROGRESS, TaskStatus.OBSERVED),
            (TaskStatus.PENDING, TaskStatus.CANCELLED),
            (TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED),
            (TaskStatus.OBSERVED, TaskStatus.CANCELLED),
        }
        if (task.status, new_status) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status transition for SUPERVISOR",
            )
    elif current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    _apply_task_status(task, new_status)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: UUID, payload: TaskComplete, current_user: User) -> Task:
    task = get_task_or_404(db, task_id)
    if current_user.role == UserRole.WORKER and task.assigned_to != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role in {UserRole.WORKER, UserRole.SUPERVISOR} and not can_close_assigned_task(
        current_user, task.event_id, db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Event is not open for task completion",
        )
    if current_user.role == UserRole.WORKER and task.status != TaskStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WORKER can only complete tasks that are IN_PROGRESS",
        )
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.SUPERVISOR and not can_manage_event(
        current_user, task.event_id, db
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.SUPERVISOR and task.assigned_to == current_user.id:
        if task.status not in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SUPERVISOR can only complete assigned tasks that are PENDING or IN_PROGRESS",
            )

    task.status = TaskStatus.COMPLETED
    task.completed_at = payload.completed_at or datetime.utcnow()
    if not task.started_at:
        task.started_at = task.completed_at
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_my_tasks(
    db: Session,
    *,
    current_user: User,
    status_filter: TaskStatus | None,
    page: int,
    limit: int,
) -> tuple[list[Task], int]:
    filters = [
        Task.assigned_to == current_user.id,
        Event.id == Task.event_id,
        Event.hidden_from_operations.is_(False),
        Event.status != EventStatus.QUOTE,
    ]
    if status_filter is not None:
        filters.append(Task.status == status_filter)
    total = db.scalar(select(func.count()).select_from(Task, Event).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Task)
            .select_from(Task, Event)
            .where(*filters)
            .order_by(Task.scheduled_at.is_(None), Task.scheduled_at, Task.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def _apply_task_status(task: Task, new_status: TaskStatus) -> None:
    task.status = new_status
    now = datetime.utcnow()
    if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
        task.started_at = now
    if new_status == TaskStatus.COMPLETED:
        task.completed_at = now
        if not task.started_at:
            task.started_at = now
    task.updated_at = now
