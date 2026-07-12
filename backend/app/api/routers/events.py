from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import EventStatus, UserRole
from app.schemas.event_schema import (
    EventCreate,
    EventDetailRead,
    EventListResponse,
    EventOperationalVisibilityUpdate,
    EventRead,
    EventServiceCreate,
    EventServiceRead,
    EventServiceUpdate,
    EventStatusUpdate,
    EventUpdate,
)
from app.schemas.dashboard_schema import EventDashboardResponse
from app.schemas.client_portal_schema import (
    ClientPortalConfigRead,
    ClientPortalConfigUpdate,
    ClientPortalResponse,
    ClientPortalTemplateApply,
)
from app.schemas.report_schema import ReportListResponse, ReportRead
from app.schemas.zone_schema import EventZoneCreate, EventZoneRead
from app.services import client_portal_service, dashboard_service, event_service, report_service, zone_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def create_event(
    payload: EventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    event = event_service.create_event(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_CREATED",
        module="events",
        entity_type="Event",
        entity_id=event.id,
        event_id=event.id,
        client_id=event.client_id,
        new_data=serialize_model_for_audit(event),
        request=request,
    )
    return event


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


@router.get("/{event_id}/dashboard", response_model=EventDashboardResponse)
def get_event_dashboard(
    event_id: UUID,
    session_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return dashboard_service.get_event_dashboard(db, event_id, current_user, session_id=session_id)


@router.get("/{event_id}/client-portal-config", response_model=ClientPortalConfigRead)
def get_client_portal_config(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return client_portal_service.get_config(db, event_id, current_user)


@router.put("/{event_id}/client-portal-config", response_model=ClientPortalConfigRead)
def update_client_portal_config(
    event_id: UUID,
    payload: ClientPortalConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return client_portal_service.update_config(db, event_id, payload, current_user)


@router.post("/{event_id}/client-portal-config/apply-template", response_model=ClientPortalConfigRead)
def apply_client_portal_template(
    event_id: UUID,
    payload: ClientPortalTemplateApply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return client_portal_service.apply_template(db, event_id, payload, current_user)


@router.get("/{event_id}/client-portal-preview", response_model=ClientPortalResponse)
def preview_client_portal(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return client_portal_service.preview_portal(db, event_id, current_user)


@router.get("/{event_id}/reports", response_model=ReportListResponse)
def list_event_reports(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = report_service.list_event_reports(
        db,
        event_id=event_id,
        current_user=current_user,
        page=page,
        limit=limit,
    )
    return ReportListResponse(items=items, total=total, page=page, limit=limit)


@router.post("/{event_id}/reports/final", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def generate_event_final_report(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = report_service.create_final_report(db, event_id=event_id, current_user=current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_GENERATED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        new_data=serialize_model_for_audit(report),
        request=request,
    )
    return report


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = event_service.ensure_can_access_event(db, current_user, event_id)
    old_data = serialize_model_for_audit(before)
    event = event_service.update_event(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_UPDATED",
        module="events",
        entity_type="Event",
        entity_id=event.id,
        event_id=event.id,
        client_id=event.client_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(event),
        request=request,
    )
    return event


@router.patch("/{event_id}/status", response_model=EventRead)
def update_event_status(
    event_id: UUID,
    payload: EventStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = event_service.ensure_can_access_event(db, current_user, event_id)
    old_status = before.status
    event = event_service.update_event_status(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_STATUS_CHANGED",
        module="events",
        entity_type="Event",
        entity_id=event.id,
        event_id=event.id,
        client_id=event.client_id,
        old_data={"status": old_status},
        new_data={"status": event.status},
        request=request,
    )
    return event


@router.patch(
    "/{event_id}/operational-visibility",
    response_model=EventRead,
    dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
)
def update_event_operational_visibility(
    event_id: UUID,
    payload: EventOperationalVisibilityUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = event_service.ensure_can_access_event(db, current_user, event_id)
    old_value = before.hidden_from_operations
    event = event_service.update_operational_visibility(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_OPERATIONAL_VISIBILITY_CHANGED",
        module="events",
        entity_type="Event",
        entity_id=event.id,
        event_id=event.id,
        client_id=event.client_id,
        old_data={"hidden_from_operations": old_value},
        new_data={"hidden_from_operations": event.hidden_from_operations},
        request=request,
    )
    return event


@router.delete("/{event_id}", response_model=EventRead)
def delete_event(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = event_service.ensure_can_access_event(db, current_user, event_id)
    old_data = serialize_model_for_audit(before)
    event = event_service.cancel_event(db, event_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_CANCELLED",
        module="events",
        entity_type="Event",
        entity_id=event.id,
        event_id=event.id,
        client_id=event.client_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(event),
        request=request,
    )
    return event


@router.post(
    "/{event_id}/services",
    response_model=EventServiceRead,
    status_code=status.HTTP_201_CREATED,
)
def add_event_service(
    event_id: UUID,
    payload: EventServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = event_service.add_event_service(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_SERVICE_ADDED",
        module="services",
        entity_type="EventService",
        entity_id=item.id,
        event_id=item.event_id,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = event_service.get_event_service_or_404(db, event_id, event_service_id)
    old_data = serialize_model_for_audit(before)
    item = event_service.update_event_service(
        db, event_id, event_service_id, payload, current_user
    )
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_SERVICE_UPDATED",
        module="services",
        entity_type="EventService",
        entity_id=item.id,
        event_id=item.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(item),
        request=request,
    )
    return item


@router.delete("/{event_id}/services/{event_service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_service(
    event_id: UUID,
    event_service_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    item = event_service.get_event_service_or_404(db, event_id, event_service_id)
    old_data = serialize_model_for_audit(item)
    event_service.delete_event_service(db, event_id, event_service_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="EVENT_SERVICE_REMOVED",
        module="services",
        entity_type="EventService",
        entity_id=event_service_id,
        event_id=event_id,
        old_data=old_data,
        request=request,
    )


@router.post(
    "/{event_id}/zones",
    response_model=EventZoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event_zone(
    event_id: UUID,
    payload: EventZoneCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    zone = zone_service.create_zone(db, event_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ZONE_CREATED",
        module="zones",
        entity_type="EventZone",
        entity_id=zone.id,
        event_id=zone.event_id,
        new_data=serialize_model_for_audit(zone),
        request=request,
    )
    return zone


@router.get("/{event_id}/zones", response_model=list[EventZoneRead])
def list_event_zones(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return zone_service.list_event_zones(db, event_id, current_user)
