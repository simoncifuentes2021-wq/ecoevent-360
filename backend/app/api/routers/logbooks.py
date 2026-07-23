# ruff: noqa: F405
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.logbook_schema import *  # noqa: F403
from app.schemas.incident_schema import IncidentRead
from app.schemas.task_schema import TaskRead
from app.services import logbook_service as service

router = APIRouter(tags=["logbooks"])


@router.post("/logbook-templates", response_model=TemplateRead, status_code=201)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.create_template(db, payload, current)


@router.get("/logbook-templates", response_model=TemplateList)
def list_templates(
    status_filter: LogbookTemplateStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    items, total = service.list_templates(db, current, page, limit, status_filter)
    return TemplateList(items=items, total=total, page=page, limit=limit)


@router.patch("/logbook-templates/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.update_template(db, template_id, payload, current)


@router.post(
    "/logbook-templates/{template_id}/versions", response_model=VersionRead, status_code=201
)
def new_version(
    template_id: UUID,
    source_version_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.new_version(db, template_id, current, source_version_id)


@router.post("/logbook-versions/{version_id}/publish", response_model=VersionRead)
def publish(
    version_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.publish(db, version_id, current)


@router.post("/events/{event_id}/logbooks", response_model=InstanceRead, status_code=201)
def create_instance(
    event_id: UUID,
    payload: InstanceCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.create_instance(db, event_id, payload, current)


@router.get("/me/logbooks", response_model=list[AssignmentRead])
def my_logbooks(
    status_filter: LogbookAssignmentStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.my_assignments(db, current, status_filter)


@router.put("/logbook-assignments/{assignment_id}/responses", response_model=ResponseRead)
def save_response(
    assignment_id: UUID,
    payload: ResponseSave,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.save_response(db, assignment_id, payload, current)


@router.post("/logbook-assignments/{assignment_id}/submit", response_model=AssignmentRead)
def submit(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.submit(db, assignment_id, current)


@router.post("/logbook-assignments/{assignment_id}/approve", response_model=AssignmentRead)
def approve(
    assignment_id: UUID,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.review(db, assignment_id, current, True, payload.comment)


@router.post("/logbook-assignments/{assignment_id}/request-changes", response_model=AssignmentRead)
def request_changes(
    assignment_id: UUID,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.review(db, assignment_id, current, False, payload.comment)


@router.get("/logbook-templates/{template_id}", response_model=TemplateDetail)
def template_detail(
    template_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.get_template_detail(db, template_id, current)


@router.get("/logbook-versions/{version_id}", response_model=VersionDetail)
def version_detail(
    version_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.get_version_detail(db, version_id, current)


@router.post("/logbook-templates/{template_id}/archive", response_model=TemplateRead)
def archive_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.archive_template(db, template_id, current)


@router.get("/events/{event_id}/logbooks", response_model=InstanceList)
def event_logbooks(
    event_id: UUID,
    status_filter: LogbookInstanceStatus | None = Query(None, alias="status"),
    template_id: UUID | None = Query(None),
    stage: LogbookOperationalStage | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    items, total = service.list_event_instances(
        db, event_id, current, page, limit, status_filter, template_id, stage
    )
    return InstanceList(items=items, total=total, page=page, limit=limit)


@router.get("/logbook-instances/{instance_id}", response_model=InstanceDetail)
def instance_detail(
    instance_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.get_instance_detail(db, instance_id, current)


@router.post("/logbook-instances/{instance_id}/open", response_model=InstanceRead)
def open_instance(
    instance_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.open_instance(db, instance_id, current)


@router.post("/logbook-instances/{instance_id}/cancel", response_model=InstanceRead)
def cancel_instance(
    instance_id: UUID,
    payload: CancelIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.cancel_instance(db, instance_id, payload.reason, current)


@router.post("/logbook-instances/{instance_id}/participants", response_model=list[AssignmentRead])
def add_participants(
    instance_id: UUID,
    payload: ParticipantsIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.add_participants(db, instance_id, payload.user_ids, current)


@router.delete("/logbook-instances/{instance_id}/participants/{assignment_id}", status_code=204)
def remove_participant(
    instance_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    service.remove_participant(db, instance_id, assignment_id, current)


@router.post(
    "/logbook-assignments/{assignment_id}/responses/{response_id}/evidences",
    response_model=EvidenceRead,
    status_code=201,
)
def upload_evidence(
    assignment_id: UUID,
    response_id: UUID,
    file: UploadFile = File(...),
    comment: str | None = Form(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.upload_evidence(db, assignment_id, response_id, file, comment, current)


@router.get("/logbook-evidences/{evidence_id}/access", response_model=EvidenceAccess)
def evidence_access(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.evidence_access(db, evidence_id, current)


@router.get("/logbook-evidences/{evidence_id}/content", include_in_schema=False)
def evidence_content(evidence_id: UUID, token: str, db: Session = Depends(get_db)):
    content, mime_type, filename = service.evidence_content(db, evidence_id, token)
    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.delete("/logbook-evidences/{evidence_id}", status_code=204)
def delete_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    service.delete_evidence(db, evidence_id, current)


@router.post(
    "/logbook-responses/{response_id}/incident", response_model=IncidentRead, status_code=201
)
def corrective_incident(
    response_id: UUID,
    payload: CorrectiveIncidentIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.create_corrective_incident(db, response_id, payload, current)


@router.post(
    "/logbook-responses/{response_id}/corrective-task", response_model=TaskRead, status_code=201
)
def corrective_task(
    response_id: UUID,
    payload: CorrectiveTaskIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.create_corrective_task(db, response_id, payload, current)


@router.get("/client/logbooks/{instance_id}", response_model=ClientLogbookSummary)
def client_logbook(
    instance_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.client_summary(db, instance_id, current)
