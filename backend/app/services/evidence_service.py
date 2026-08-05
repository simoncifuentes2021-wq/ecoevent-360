from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.permissions import can_access_event, can_close_assigned_task, can_manage_event, can_operate_event
from app.models.core import Event, EventSession, Evidence, Incident, Task, User
from app.models.enums import EventStatus, UserRole
from app.services.file_storage_service import delete_stored_file, read_stored_file, save_evidence_file


def get_evidence_or_404(db: Session, evidence_id: UUID) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return evidence


def _get_event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _validate_task(db: Session, event_id: UUID, task_id: UUID | None) -> None:
    if task_id is None:
        return
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task does not belong to this event",
        )


def _validate_incident(db: Session, event_id: UUID, incident_id: UUID | None) -> None:
    if incident_id is None:
        return
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if incident.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident does not belong to this event",
        )


def create_evidence(
    db: Session,
    *,
    event_id: UUID,
    task_id: UUID | None,
    incident_id: UUID | None,
    description: str | None,
    file: UploadFile,
    current_user: User,
    session_id: UUID | None = None,
) -> Evidence:
    _get_event_or_404(db, event_id)
    _validate_task(db, event_id, task_id)
    _validate_incident(db, event_id, incident_id)
    task = db.get(Task, task_id) if task_id else None
    incident = db.get(Incident, incident_id) if incident_id else None
    derived = {value for value in (task.session_id if task else None, incident.session_id if incident else None) if value is not None}
    if len(derived) > 1:
        raise HTTPException(status_code=400, detail="Task and incident belong to different shows")
    derived_session = next(iter(derived), None)
    if session_id is not None and (task_id or incident_id) and session_id != derived_session:
        raise HTTPException(status_code=400, detail="Evidence show contradicts its task or incident")
    resolved_session = derived_session or session_id
    if resolved_session is not None:
        show = db.get(EventSession, resolved_session)
        if not show or show.event_id != event_id:
            raise HTTPException(status_code=400, detail="Event session does not belong to this event")
        if show.archived_at:
            raise HTTPException(status_code=400, detail="Archived shows cannot receive new evidence")
    can_upload_for_assigned_task = False
    if task_id and current_user.role == UserRole.WORKER:
        task = db.get(Task, task_id)
        can_upload_for_assigned_task = (
            task is not None
            and task.assigned_to == current_user.id
            and can_close_assigned_task(current_user, event_id, db)
        )
    if not can_operate_event(current_user, event_id, db) and not can_upload_for_assigned_task:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    file_url, file_type = save_evidence_file(file)
    evidence = Evidence(
        event_id=event_id,
        task_id=task_id,
        incident_id=incident_id,
        session_id=resolved_session if not (task_id or incident_id) else None,
        uploaded_by=current_user.id,
        file_url=file_url,
        file_type=file_type,
        description=description,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def list_event_evidences(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    page: int,
    limit: int,
    session_id: UUID | None = None,
    scope: str | None = None,
) -> tuple[list[Evidence], int]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [Evidence.event_id == event_id]
    derived_session = func.coalesce(Task.session_id, Incident.session_id, Evidence.session_id)
    if scope == "general":
        filters.append(derived_session.is_(None))
    elif scope in {"session", "general_and_session"} or session_id is not None:
        if session_id is None:
            raise HTTPException(status_code=400, detail="session_id is required")
        filters.append(or_(derived_session == session_id, derived_session.is_(None)) if scope == "general_and_session" else derived_session == session_id)
    base = Evidence.__table__.outerjoin(Task, Evidence.task_id == Task.id).outerjoin(Incident, Evidence.incident_id == Incident.id)
    total = db.scalar(select(func.count(Evidence.id)).select_from(base).where(*filters)) or 0
    rows = db.execute(
            select(Evidence, derived_session.label("resolved_session_id")).select_from(base)
            .where(*filters)
            .order_by(Evidence.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    items = []
    for evidence, resolved_session_id in rows:
        if evidence.session_id is None:
            set_committed_value(evidence, "session_id", resolved_session_id)
        items.append(evidence)
    return items, total


def get_evidence(db: Session, evidence_id: UUID, current_user: User) -> Evidence:
    evidence = get_evidence_or_404(db, evidence_id)
    if not can_access_event(current_user, evidence.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return evidence


def download_evidence(db: Session, evidence_id: UUID, current_user: User) -> tuple[bytes, str, str]:
    evidence = get_evidence(db, evidence_id, current_user)
    content, mime = read_stored_file(evidence.file_url)
    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(mime, "")
    return content, mime, f"evidencia-{evidence.id}{extension}"


def delete_evidence(db: Session, evidence_id: UUID, current_user: User) -> None:
    evidence = get_evidence_or_404(db, evidence_id)
    event = _get_event_or_404(db, evidence.event_id)
    if not can_access_event(current_user, evidence.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if not can_manage_event(current_user, evidence.event_id, db) and not (
        current_user.role == UserRole.WORKER and evidence.uploaded_by == current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if event.status in {EventStatus.FINISHED, EventStatus.REPORT_DELIVERED}:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can delete evidence from finished events",
            )

    file_url = evidence.file_url
    db.delete(evidence)
    db.commit()
    delete_stored_file(file_url)
