from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.zone_schema import EventZoneRead, EventZoneUpdate
from app.services import zone_service

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return zone_service.update_zone(db, zone_id, payload, current_user)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    zone_service.delete_zone(db, zone_id, current_user)
