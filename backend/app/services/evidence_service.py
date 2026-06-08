from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import can_access_event, can_close_assigned_task, can_operate_event
from app.models.core import Event, Evidence, Incident, Task, User
from app.models.enums import EventStatus, UserRole
from app.services.file_storage_service import delete_local_file, save_evidence_file


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
) -> Evidence:
    _get_event_or_404(db, event_id)
    _validate_task(db, event_id, task_id)
    _validate_incident(db, event_id, incident_id)
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
) -> tuple[list[Evidence], int]:
    _get_event_or_404(db, event_id)
    if not can_access_event(current_user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    filters = [Evidence.event_id == event_id]
    total = db.scalar(select(func.count()).select_from(Evidence).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Evidence)
            .where(*filters)
            .order_by(Evidence.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def get_evidence(db: Session, evidence_id: UUID, current_user: User) -> Evidence:
    evidence = get_evidence_or_404(db, evidence_id)
    if not can_access_event(current_user, evidence.event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return evidence


def delete_evidence(db: Session, evidence_id: UUID, current_user: User) -> None:
    evidence = get_evidence_or_404(db, evidence_id)
    event = _get_event_or_404(db, evidence.event_id)
    if not can_access_event(current_user, evidence.event_id, db):
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
    delete_local_file(file_url)
