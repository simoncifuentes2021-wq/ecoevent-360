from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event, can_operate_event
from app.models.core import Event, EventStaff, EventZone, Incident, User
from app.models.enums import IncidentStatus, UserRole
from app.schemas.incident_schema import IncidentCreate, IncidentResolve, IncidentUpdate


def get_incident_or_404(db: Session, incident_id: UUID) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


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
    assigned = db.scalar(
        select(EventStaff.id).where(EventStaff.event_id == event_id, EventStaff.user_id == user_id)
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be assigned to the event staff",
        )


def _ensure_can_manage_incident(db: Session, incident: Incident, current_user: User) -> None:
    if not can_manage_event(current_user, incident.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def create_incident(
    db: Session, event_id: UUID, payload: IncidentCreate, current_user: User
) -> Incident:
    _get_event_or_404(db, event_id)
    if not can_operate_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    _validate_zone(db, event_id, payload.zone_id)
    _validate_assignee(db, event_id, payload.assigned_to)

    incident = Incident(
        event_id=event_id,
        reported_by=current_user.id,
        status=IncidentStatus.ASSIGNED if payload.assigned_to else IncidentStatus.REPORTED,
        source="INTERNAL",
        **payload.model_dump(),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_event_incidents(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    status_filter: IncidentStatus | None,
    page: int,
    limit: int,
) -> tuple[list[Incident], int]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [Incident.event_id == event_id]
    if status_filter is not None:
        filters.append(Incident.status == status_filter)

    total = db.scalar(select(func.count()).select_from(Incident).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Incident)
            .where(*filters)
            .order_by(Incident.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_incident(db: Session, incident_id: UUID, current_user: User) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    if not can_access_event(current_user, incident.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return incident


def update_incident(
    db: Session, incident_id: UUID, payload: IncidentUpdate, current_user: User
) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    _ensure_can_manage_incident(db, incident, current_user)

    data = payload.model_dump(exclude_unset=True)
    if "zone_id" in data:
        _validate_zone(db, incident.event_id, data["zone_id"])
    if "assigned_to" in data:
        _validate_assignee(db, incident.event_id, data["assigned_to"])
        if data["assigned_to"] and incident.status == IncidentStatus.REPORTED:
            incident.status = IncidentStatus.ASSIGNED

    for field, value in data.items():
        setattr(incident, field, value)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def resolve_incident(
    db: Session, incident_id: UUID, payload: IncidentResolve, current_user: User
) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    _ensure_can_manage_incident(db, incident, current_user)
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = payload.resolved_at or datetime.utcnow()
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def close_incident(db: Session, incident_id: UUID, current_user: User) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    _ensure_can_manage_incident(db, incident, current_user)
    incident.status = IncidentStatus.CLOSED
    incident.closed_at = datetime.utcnow()
    if not incident.resolved_at:
        incident.resolved_at = incident.closed_at
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
