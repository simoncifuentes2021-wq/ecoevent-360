from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_manage_event, can_operate_event
from app.models.core import Event, EventSession, EventStaff, EventZone, Evidence, Incident, Task, User
from app.models.enums import IncidentStatus, TaskStatus, UserRole
from app.schemas.incident_schema import IncidentCorrectiveTaskCreate, IncidentCreate, IncidentResolve, IncidentUpdate


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


def _validate_session(db: Session, event_id: UUID, session_id: UUID | None) -> None:
    if session_id is None:
        return
    session = db.get(EventSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Event session not found")
    if session.event_id != event_id:
        raise HTTPException(status_code=400, detail="Event session does not belong to this event")
    if session.archived_at:
        raise HTTPException(status_code=400, detail="Archived shows cannot receive new incidents")


def _resolve_source_task(db: Session, event_id: UUID, task_id: UUID | None) -> Task | None:
    if task_id is None:
        return None
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Source task not found")
    if task.event_id != event_id:
        raise HTTPException(status_code=400, detail="Source task does not belong to this event")
    return task


def _has_reassignment_activity(db: Session, incident: Incident) -> bool:
    from app.models.logbook import LogbookIncidentLink

    return bool(
        incident.status != IncidentStatus.REPORTED or incident.resolved_at or incident.closed_at
        or db.scalar(select(Evidence.id).where(Evidence.incident_id == incident.id).limit(1))
        or db.scalar(select(Task.id).where(Task.source_incident_id == incident.id).limit(1))
        or db.scalar(select(LogbookIncidentLink.id).where(LogbookIncidentLink.incident_id == incident.id).limit(1))
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
    source_task = _resolve_source_task(db, event_id, payload.source_task_id)
    session_id = source_task.session_id if source_task else payload.session_id
    if source_task and payload.session_id is not None and payload.session_id != source_task.session_id:
        raise HTTPException(status_code=400, detail="Incident show contradicts its source task")
    _validate_session(db, event_id, session_id)

    incident = Incident(
        event_id=event_id,
        reported_by=current_user.id,
        status=IncidentStatus.ASSIGNED if payload.assigned_to else IncidentStatus.REPORTED,
        source="INTERNAL",
        **payload.model_dump(exclude={"session_id"}),
        session_id=session_id,
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
    session_id: UUID | None = None,
    scope: str | None = None,
) -> tuple[list[Incident], int]:
    _get_event_or_404(db, event_id)
    if current_user.role in {UserRole.CLIENT, UserRole.LOGISTICS_OPERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incidents are not authorized for this role")
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [Incident.event_id == event_id]
    if current_user.role == UserRole.WORKER:
        filters.append(or_(Incident.reported_by == current_user.id, Incident.assigned_to == current_user.id))
    if status_filter is not None:
        filters.append(Incident.status == status_filter)
    if scope == "general":
        filters.append(Incident.session_id.is_(None))
    elif scope == "session":
        if session_id is None:
            raise HTTPException(status_code=400, detail="session_id is required for session scope")
        _validate_session(db, event_id, session_id)
        filters.append(Incident.session_id == session_id)
    elif scope == "general_and_session":
        if session_id is None:
            raise HTTPException(status_code=400, detail="session_id is required for general_and_session scope")
        _validate_session(db, event_id, session_id)
        filters.append((Incident.session_id == session_id) | Incident.session_id.is_(None))
    elif session_id is not None:
        _validate_session(db, event_id, session_id)
        filters.append(Incident.session_id == session_id)

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
    if current_user.role in {UserRole.CLIENT, UserRole.LOGISTICS_OPERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incidents are not authorized for this role")
    if not can_access_event(current_user, incident.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if current_user.role == UserRole.WORKER and current_user.id not in {incident.reported_by, incident.assigned_to}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return incident


def update_incident(
    db: Session, incident_id: UUID, payload: IncidentUpdate, current_user: User
) -> Incident:
    incident = get_incident_or_404(db, incident_id)
    _ensure_can_manage_incident(db, incident, current_user)

    data = payload.model_dump(exclude_unset=True)
    reason = data.pop("reassignment_reason", None)
    if "zone_id" in data:
        _validate_zone(db, incident.event_id, data["zone_id"])
    if "assigned_to" in data:
        _validate_assignee(db, incident.event_id, data["assigned_to"])
        if data["assigned_to"] and incident.status == IncidentStatus.REPORTED:
            incident.status = IncidentStatus.ASSIGNED
    if "session_id" in data and data["session_id"] != incident.session_id:
        _validate_session(db, incident.event_id, data["session_id"])
        if incident.source_task_id:
            raise HTTPException(status_code=409, detail="Incident show is inherited from its source task")
        if _has_reassignment_activity(db, incident):
            raise HTTPException(status_code=409, detail="Incident with operational activity cannot be reassigned")
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="reassignment_reason is required when changing show")

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


def create_corrective_task(db: Session, incident_id: UUID, payload: IncidentCorrectiveTaskCreate, current_user: User) -> Task:
    incident = get_incident_or_404(db, incident_id)
    _ensure_can_manage_incident(db, incident, current_user)
    _validate_assignee(db, incident.event_id, payload.assigned_to)
    existing = db.scalar(select(Task.id).where(Task.source_incident_id == incident.id).limit(1))
    if existing:
        raise HTTPException(status_code=409, detail="A corrective task already exists for this incident")
    task = Task(event_id=incident.event_id, session_id=incident.session_id, source_incident_id=incident.id, created_by=current_user.id, status=TaskStatus.PENDING, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
