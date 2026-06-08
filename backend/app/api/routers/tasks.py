from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import TaskStatus
from app.schemas.task_schema import (
    TaskComplete,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services import task_service
from app.services.audit_log_service import create_audit_log

router = APIRouter(tags=["tasks"])


@router.post(
    "/events/{event_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    event_id: UUID,
    payload: TaskCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = task_service.create_task(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CREATE",
        module="tasks",
        entity_type="Task",
        entity_id=task.id,
        event_id=task.event_id,
        new_data={"id": task.id, "title": task.title, "status": task.status},
        request=request,
    )
    return task


@router.get("/events/{event_id}/tasks", response_model=TaskListResponse)
def list_event_tasks(
    event_id: UUID,
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    assigned_to: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = task_service.list_event_tasks(
        db,
        event_id=event_id,
        current_user=current_user,
        status_filter=status_filter,
        assigned_to=assigned_to,
        page=page,
        limit=limit,
    )
    return TaskListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return task_service.get_task(db, task_id, current_user)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = task_service.get_task(db, task_id, current_user)
    old_data = {
        "title": before.title,
        "status": before.status,
        "priority": before.priority,
        "assigned_to": before.assigned_to,
        "zone_id": before.zone_id,
    }
    task = task_service.update_task(db, task_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="UPDATE",
        module="tasks",
        entity_type="Task",
        entity_id=task.id,
        event_id=task.event_id,
        old_data=old_data,
        new_data=payload.model_dump(exclude_unset=True),
        request=request,
    )
    return task


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: UUID,
    payload: TaskStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = task_service.get_task(db, task_id, current_user)
    old_status = before.status
    task = task_service.update_task_status(db, task_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="STATUS_CHANGE",
        module="tasks",
        entity_type="Task",
        entity_id=task.id,
        event_id=task.event_id,
        old_data={"status": old_status},
        new_data={"status": task.status},
        request=request,
    )
    return task


@router.patch("/tasks/{task_id}/complete", response_model=TaskRead)
def complete_task(
    task_id: UUID,
    payload: TaskComplete,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = task_service.complete_task(db, task_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="COMPLETE",
        module="tasks",
        entity_type="Task",
        entity_id=task.id,
        event_id=task.event_id,
        new_data={"status": task.status, "completed_at": task.completed_at},
        request=request,
    )
    return task


@router.get("/me/tasks", response_model=TaskListResponse)
def list_my_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = task_service.list_my_tasks(
        db,
        current_user=current_user,
        status_filter=status_filter,
        page=page,
        limit=limit,
    )
    return TaskListResponse(items=items, total=total, page=page, limit=limit)
