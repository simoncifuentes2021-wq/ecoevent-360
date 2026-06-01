from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.models.enums import IncidentStatus
from app.schemas.incident_schema import (
    IncidentCreate,
    IncidentListResponse,
    IncidentRead,
    IncidentResolve,
    IncidentUpdate,
)
from app.services import incident_service

router = APIRouter(tags=["incidents"])


@router.post(
    "/events/{event_id}/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    event_id: UUID,
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return incident_service.create_incident(db, event_id, payload, current_user)


@router.get("/events/{event_id}/incidents", response_model=IncidentListResponse)
def list_event_incidents(
    event_id: UUID,
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return incident_service.update_incident(db, incident_id, payload, current_user)


@router.patch("/incidents/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(
    incident_id: UUID,
    payload: IncidentResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return incident_service.resolve_incident(db, incident_id, payload, current_user)


@router.patch("/incidents/{incident_id}/close", response_model=IncidentRead)
def close_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return incident_service.close_incident(db, incident_id, current_user)
