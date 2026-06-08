from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.evidence_schema import EvidenceListResponse, EvidenceRead
from app.services import evidence_service
from app.services.audit_log_service import create_audit_log

router = APIRouter(tags=["evidences"])


@router.post(
    "/evidences",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    request: Request,
    event_id: UUID = Form(...),
    task_id: UUID | None = Form(default=None),
    incident_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = evidence_service.create_evidence(
        db,
        event_id=event_id,
        task_id=task_id,
        incident_id=incident_id,
        description=description,
        file=file,
        current_user=current_user,
    )
    create_audit_log(
        db,
        user=current_user,
        action="CREATE",
        module="evidences",
        entity_type="Evidence",
        entity_id=evidence.id,
        event_id=evidence.event_id,
        new_data={
            "id": evidence.id,
            "task_id": evidence.task_id,
            "incident_id": evidence.incident_id,
            "file_type": evidence.file_type,
        },
        request=request,
    )
    return evidence


@router.get("/events/{event_id}/evidences", response_model=EvidenceListResponse)
def list_event_evidences(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    items, total = evidence_service.list_event_evidences(
        db, event_id=event_id, current_user=current_user, page=page, limit=limit
    )
    return EvidenceListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/evidences/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return evidence_service.get_evidence(db, evidence_id, current_user)


@router.delete("/evidences/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    evidence = evidence_service.get_evidence(db, evidence_id, current_user)
    event_id = evidence.event_id
    old_data = {"id": evidence.id, "file_url": evidence.file_url, "file_type": evidence.file_type}
    evidence_service.delete_evidence(db, evidence_id, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="DELETE",
        module="evidences",
        entity_type="Evidence",
        entity_id=evidence_id,
        event_id=event_id,
        old_data=old_data,
        request=request,
    )
