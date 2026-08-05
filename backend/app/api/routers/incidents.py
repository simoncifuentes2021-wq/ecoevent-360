from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import IncidentStatus
from app.schemas.incident_schema import (
    IncidentCreate,
    IncidentCorrectiveTaskCreate,
    IncidentListResponse,
    IncidentRead,
    IncidentResolve,
    IncidentUpdate,
)
from app.services import incident_service
from app.services.audit_log_service import create_audit_log
from app.schemas.task_schema import TaskRead

router = APIRouter(tags=["incidents"])


@router.post(
    "/events/{event_id}/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    event_id: UUID,
    payload: IncidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    incident = incident_service.create_incident(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CREATE",
        module="incidents",
        entity_type="Incident",
        entity_id=incident.id,
        event_id=incident.event_id,
        new_data={"id": incident.id, "title": incident.title, "status": incident.status, "session_id": incident.session_id, "source_task_id": incident.source_task_id},
        request=request,
    )
    return incident


@router.get("/events/{event_id}/incidents", response_model=IncidentListResponse)
def list_event_incidents(
    event_id: UUID,
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session_id: UUID | None = None,
    scope: str | None = Query(default=None, pattern="^(general|session|general_and_session)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = incident_service.list_event_incidents(
        db,
        event_id=event_id,
        current_user=current_user,
        status_filter=status_filter,
        page=page,
        limit=limit,
        session_id=session_id,
        scope=scope,
    )
    return IncidentListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return incident_service.get_incident(db, incident_id, current_user)


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: UUID,
    payload: IncidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = incident_service.get_incident(db, incident_id, current_user)
    old_data = {
        "title": before.title,
        "status": before.status,
        "priority": before.priority,
        "assigned_to": before.assigned_to,
        "session_id": before.session_id,
    }
    incident = incident_service.update_incident(db, incident_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="INCIDENT_SESSION_REASSIGNED" if "session_id" in payload.model_fields_set and old_data["session_id"] != incident.session_id else "UPDATE",
        module="incidents",
        entity_type="Incident",
        entity_id=incident.id,
        event_id=incident.event_id,
        old_data=old_data,
        new_data=payload.model_dump(exclude_unset=True),
        metadata={"session_id": incident.session_id, "reassignment_reason": payload.reassignment_reason} if "session_id" in payload.model_fields_set else None,
        request=request,
    )
    return incident


@router.patch("/incidents/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(
    incident_id: UUID,
    payload: IncidentResolve,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    incident = incident_service.resolve_incident(db, incident_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="RESOLVE",
        module="incidents",
        entity_type="Incident",
        entity_id=incident.id,
        event_id=incident.event_id,
        new_data={"status": incident.status, "resolved_at": incident.resolved_at},
        request=request,
    )
    return incident


@router.patch("/incidents/{incident_id}/close", response_model=IncidentRead)
def close_incident(
    incident_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    incident = incident_service.close_incident(db, incident_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="CLOSE",
        module="incidents",
        entity_type="Incident",
        entity_id=incident.id,
        event_id=incident.event_id,
        new_data={"status": incident.status, "closed_at": incident.closed_at},
        request=request,
    )
    return incident


@router.post("/incidents/{incident_id}/corrective-task", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_corrective_task(incident_id: UUID, payload: IncidentCorrectiveTaskCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    task = incident_service.create_corrective_task(db, incident_id, payload, current_user)
    create_audit_log(db, user=current_user, action="INCIDENT_CORRECTIVE_TASK_CREATED", module="incidents", entity_type="Task", entity_id=task.id, event_id=task.event_id, incident_id=incident_id, task_id=task.id, new_data={"session_id": task.session_id, "source_incident_id": incident_id}, request=request)
    return task
