from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import EventStatus, UserRole
from app.schemas.event_schema import (
    EventCreate,
    EventDetailRead,
    EventListResponse,
    EventRead,
    EventServiceCreate,
    EventServiceRead,
    EventServiceUpdate,
    EventStatusUpdate,
    EventUpdate,
)
from app.schemas.zone_schema import EventZoneCreate, EventZoneRead
from app.services import event_service, zone_service

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.create_event(db, payload, current_user)


@router.get("", response_model=EventListResponse)
def list_events(
    q: str | None = None,
    status_filter: EventStatus | None = Query(default=None, alias="status"),
    client_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = event_service.list_events(
        db,
        current_user=current_user,
        q=q,
        status_filter=status_filter,
        client_id=client_id,
        page=page,
        limit=limit,
    )
    return EventListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{event_id}", response_model=EventDetailRead)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    event, services_count, zones_count = event_service.get_event_detail(db, event_id, current_user)
    return EventDetailRead(
        **EventRead.model_validate(event).model_dump(),
        client=event.client,
        services_count=services_count,
        zones_count=zones_count,
    )


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.update_event(db, event_id, payload, current_user)


@router.patch("/{event_id}/status", response_model=EventRead)
def update_event_status(
    event_id: UUID,
    payload: EventStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.update_event_status(db, event_id, payload, current_user)


@router.delete("/{event_id}", response_model=EventRead)
def delete_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.cancel_event(db, event_id, current_user)


@router.post(
    "/{event_id}/services",
    response_model=EventServiceRead,
    status_code=status.HTTP_201_CREATED,
)
def add_event_service(
    event_id: UUID,
    payload: EventServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.add_event_service(db, event_id, payload, current_user)


@router.get("/{event_id}/services", response_model=list[EventServiceRead])
def list_event_services(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.list_event_services(db, event_id, current_user)


@router.patch("/{event_id}/services/{event_service_id}", response_model=EventServiceRead)
def update_event_service(
    event_id: UUID,
    event_service_id: UUID,
    payload: EventServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return event_service.update_event_service(
        db, event_id, event_service_id, payload, current_user
    )


@router.delete("/{event_id}/services/{event_service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_service(
    event_id: UUID,
    event_service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    event_service.delete_event_service(db, event_id, event_service_id, current_user)


@router.post(
    "/{event_id}/zones",
    response_model=EventZoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event_zone(
    event_id: UUID,
    payload: EventZoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return zone_service.create_zone(db, event_id, payload, current_user)


@router.get("/{event_id}/zones", response_model=list[EventZoneRead])
def list_event_zones(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return zone_service.list_event_zones(db, event_id, current_user)
