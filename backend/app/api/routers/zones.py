from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.zone_schema import EventZoneRead, EventZoneUpdate
from app.services import zone_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/zones", tags=["event zones"])


@router.get("/{zone_id}", response_model=EventZoneRead)
def get_zone(
    zone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return zone_service.get_zone(db, zone_id, current_user)


@router.patch("/{zone_id}", response_model=EventZoneRead)
def update_zone(
    zone_id: UUID,
    payload: EventZoneUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = zone_service.get_zone(db, zone_id, current_user)
    old_data = serialize_model_for_audit(before)
    zone = zone_service.update_zone(db, zone_id, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ZONE_UPDATED",
        module="zones",
        entity_type="EventZone",
        entity_id=zone.id,
        event_id=zone.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(zone),
        request=request,
    )
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    zone = zone_service.get_zone(db, zone_id, current_user)
    event_id = zone.event_id
    old_data = serialize_model_for_audit(zone)
    zone_service.delete_zone(db, zone_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="ZONE_DEACTIVATED",
        module="zones",
        entity_type="EventZone",
        entity_id=zone_id,
        event_id=event_id,
        old_data=old_data,
        request=request,
    )
