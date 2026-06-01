from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import EventZone, Incident, SurveyResponse, Task, User, WasteRecord
from app.models.enums import UserRole
from app.schemas.zone_schema import EventZoneCreate, EventZoneUpdate
from app.services.event_service import get_event_or_404


def get_zone_or_404(db: Session, zone_id: UUID) -> EventZone:
    zone = db.get(EventZone, zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return zone


def _ensure_zone_name_available(
    db: Session, event_id: UUID, name: str, exclude_zone_id: UUID | None = None
) -> None:
    filters = [EventZone.event_id == event_id, func.lower(EventZone.name) == name.lower()]
    if exclude_zone_id:
        filters.append(EventZone.id != exclude_zone_id)
    exists = db.scalar(select(EventZone.id).where(*filters).limit(1))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zone name already exists for this event",
        )


def create_zone(
    db: Session, event_id: UUID, payload: EventZoneCreate, current_user: User
) -> EventZone:
    get_event_or_404(db, event_id)
    if not can_manage_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    _ensure_zone_name_available(db, event_id, payload.name)
    zone = EventZone(event_id=event_id, **payload.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def list_event_zones(db: Session, event_id: UUID, current_user: User) -> list[EventZone]:
    get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return list(
        db.scalars(
            select(EventZone).where(EventZone.event_id == event_id).order_by(EventZone.created_at)
        ).all()
    )


def get_zone(db: Session, zone_id: UUID, current_user: User) -> EventZone:
    zone = get_zone_or_404(db, zone_id)
    if not can_access_event(current_user, zone.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return zone


def update_zone(
    db: Session, zone_id: UUID, payload: EventZoneUpdate, current_user: User
) -> EventZone:
    zone = get_zone_or_404(db, zone_id)
    if not can_manage_event(current_user, zone.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.WORKER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        _ensure_zone_name_available(db, zone.event_id, data["name"], exclude_zone_id=zone.id)
    for field, value in data.items():
        setattr(zone, field, value)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone_id: UUID, current_user: User) -> None:
    zone = get_zone_or_404(db, zone_id)
    if current_user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    has_dependencies = any(
        db.scalar(select(model.id).where(model.zone_id == zone_id).limit(1))
        for model in (Task, Incident, WasteRecord, SurveyResponse)
    )
    if has_dependencies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete zone with related operational data",
        )

    db.delete(zone)
    db.commit()
