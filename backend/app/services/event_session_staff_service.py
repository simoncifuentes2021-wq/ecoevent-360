from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Event, EventSession, EventSessionStaff, EventStaff, Evidence, Incident, Task, User
from app.models.enums import UserRole
from app.schemas.event_session_staff_schema import EventSessionStaffCreate, EventSessionStaffUpdate


def _session(db: Session, session_id: UUID) -> EventSession:
    item = db.get(EventSession, session_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event session not found")
    return item


def _assignment(db: Session, assignment_id: UUID) -> EventSessionStaff:
    item = db.get(EventSessionStaff, assignment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Show staff assignment not found")
    return item


def _validate_shift(db: Session, event_id: UUID, start: datetime | None, end: datetime | None) -> None:
    if start and end and start >= end:
        raise HTTPException(status_code=400, detail="shift_start must be before shift_end")
    event = db.get(Event, event_id)
    if (start and start < event.start_date) or (end and end > event.end_date):
        raise HTTPException(status_code=400, detail="Shift must be inside the event dates")


def _overlap(db: Session, item: EventSessionStaff) -> bool:
    if not item.shift_start or not item.shift_end:
        return False
    return db.scalar(select(EventSessionStaff.id).where(
        EventSessionStaff.id != item.id,
        EventSessionStaff.event_staff_id == item.event_staff_id,
        EventSessionStaff.shift_start < item.shift_end,
        EventSessionStaff.shift_end > item.shift_start,
    ).limit(1)) is not None


def create_assignment(db: Session, session_id: UUID, payload: EventSessionStaffCreate, current_user: User):
    session = _session(db, session_id)
    if not can_manage_event(current_user, session.event_id, db):
        raise HTTPException(status_code=403, detail="Insufficient role")
    staff = db.get(EventStaff, payload.event_staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Event staff assignment not found")
    if staff.event_id != session.event_id:
        raise HTTPException(status_code=400, detail="Event staff does not belong to the show event")
    _validate_shift(db, session.event_id, payload.shift_start, payload.shift_end)
    item = EventSessionStaff(event_id=session.event_id, session_id=session.id, created_by=current_user.id, **payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Person is already assigned to this show")
    db.refresh(item)
    item.overlap_warning = _overlap(db, item)
    return item


def list_assignments(db: Session, session_id: UUID, current_user: User, page: int, limit: int):
    session = _session(db, session_id)
    if not can_access_event(current_user, session.event_id, db):
        raise HTTPException(status_code=403, detail="Insufficient role")
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Show staffing is internal")
    filters = [EventSessionStaff.session_id == session_id]
    if current_user.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}:
        filters.append(EventStaff.user_id == current_user.id)
    total = db.scalar(select(func.count()).select_from(EventSessionStaff).join(EventStaff).where(*filters)) or 0
    items = list(db.scalars(select(EventSessionStaff).join(EventStaff).options(joinedload(EventSessionStaff.event_staff).joinedload(EventStaff.user)).where(*filters).order_by(EventSessionStaff.shift_start, EventSessionStaff.created_at).offset((page - 1) * limit).limit(limit)).unique().all())
    for item in items:
        item.overlap_warning = _overlap(db, item)
        item.user = item.event_staff.user
    return items, total


def update_assignment(db: Session, assignment_id: UUID, payload: EventSessionStaffUpdate, current_user: User):
    item = _assignment(db, assignment_id)
    if not can_manage_event(current_user, item.event_id, db):
        raise HTTPException(status_code=403, detail="Insufficient role")
    data = payload.model_dump(exclude_unset=True)
    _validate_shift(db, item.event_id, data.get("shift_start", item.shift_start), data.get("shift_end", item.shift_end))
    for field, value in data.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(item)
    item.overlap_warning = _overlap(db, item)
    return item


def delete_assignment(db: Session, assignment_id: UUID, current_user: User) -> EventSessionStaff:
    item = _assignment(db, assignment_id)
    if not can_manage_event(current_user, item.event_id, db):
        raise HTTPException(status_code=403, detail="Insufficient role")
    db.delete(item)
    db.commit()
    return item


def list_person_sessions(db: Session, event_staff_id: UUID, current_user: User):
    staff = db.get(EventStaff, event_staff_id)
    if not staff or not can_access_event(current_user, staff.event_id, db):
        raise HTTPException(status_code=404, detail="Event staff assignment not found")
    if current_user.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR} and staff.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return list(db.scalars(select(EventSessionStaff).where(EventSessionStaff.event_staff_id == event_staff_id).order_by(EventSessionStaff.shift_start)).all())


def operational_summary(db: Session, session_id: UUID, current_user: User) -> dict:
    session = _session(db, session_id)
    if not can_access_event(current_user, session.event_id, db):
        raise HTTPException(status_code=403, detail="Insufficient role")
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Show operations are internal")
    task_filters = [Task.session_id == session_id]
    incident_filters = [Incident.session_id == session_id]
    staff_query = select(func.count()).select_from(EventSessionStaff).join(EventStaff)
    active_staff_query = staff_query.where(EventSessionStaff.shift_start.is_not(None), EventSessionStaff.shift_end.is_not(None))
    evidence_filters = [or_(Evidence.session_id == session_id, Task.session_id == session_id, Incident.session_id == session_id)]
    if current_user.role in {UserRole.WORKER, UserRole.LOGISTICS_OPERATOR}:
        staff_query = staff_query.where(EventStaff.user_id == current_user.id)
        active_staff_query = active_staff_query.where(EventStaff.user_id == current_user.id)
        task_filters.append(Task.assigned_to == current_user.id)
        incident_filters.append(or_(Incident.reported_by == current_user.id, Incident.assigned_to == current_user.id))
        evidence_filters.append(Evidence.uploaded_by == current_user.id)
    task_rows = db.execute(select(Task.status, func.count()).where(*task_filters).group_by(Task.status)).all()
    incident_rows = db.execute(select(Incident.status, func.count()).where(*incident_filters).group_by(Incident.status)).all()
    evidence_count = db.scalar(select(func.count()).select_from(Evidence).outerjoin(Task, Evidence.task_id == Task.id).outerjoin(Incident, Evidence.incident_id == Incident.id).where(*evidence_filters)) or 0
    return {
        "staff_count": db.scalar(staff_query.where(EventSessionStaff.session_id == session_id)) or 0,
        "active_shift_count": db.scalar(active_staff_query.where(EventSessionStaff.session_id == session_id)) or 0,
        "tasks_by_status": dict(task_rows), "incidents_by_status": dict(incident_rows), "evidence_count": evidence_count,
    }
