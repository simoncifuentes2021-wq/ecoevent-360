# ruff: noqa: F405
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user, require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.enums import UserRole
from app.schemas.logbook_schema import *  # noqa: F403
from app.schemas.incident_schema import IncidentRead
from app.schemas.task_schema import TaskRead
from app.services import logbook_service as service
from app.services import logbook_recurrence_service as recurrence
from app.services import logbook_excel_service as excel_import
from app.services import logbook_contribution_service as contributions

router = APIRouter(tags=["logbooks"])


@router.post("/events/{event_id}/logbooks/import-xlsx/preview", response_model=dict)
async def preview_logbook_xlsx(
    event_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    content = await file.read(excel_import.MAX_FILE_SIZE + 1)
    return excel_import.preview(db, event_id, content, file.filename or "", current)


@router.get("/events/{event_id}/logbooks/import-xlsx/template")
def download_logbook_xlsx_template(
    event_id: UUID, start_date: date = Query(...), end_date: date = Query(...),
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    content, filename = excel_import.generate_template(
        db, event_id, start_date, end_date, current
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/events/{event_id}/logbooks/import-xlsx", response_model=dict, status_code=201)
async def confirm_logbook_xlsx(
    event_id: UUID, configuration: str = Form(...), file: UploadFile = File(...),
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    config = LogbookImportConfig.model_validate_json(configuration)
    content = await file.read(excel_import.MAX_FILE_SIZE + 1)
    return excel_import.import_xlsx(db, event_id, content, file.filename or "", config, current)


@router.post(
    "/logbook-import-batches/{batch_id}/participants/preview",
    response_model=LogbookImportBulkParticipantsRead,
)
def preview_import_participants_bulk(
    batch_id: UUID, payload: LogbookImportBulkParticipantsIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return excel_import.bulk_participants(db, batch_id, payload, current, apply=False)


@router.patch(
    "/logbook-import-batches/{batch_id}/participants",
    response_model=LogbookImportBulkParticipantsRead,
)
def update_import_participants_bulk(
    batch_id: UUID, payload: LogbookImportBulkParticipantsIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return excel_import.bulk_participants(db, batch_id, payload, current, apply=True)


@router.post(
    "/logbook-import-batches/{batch_id}/supervisor/preview",
    response_model=LogbookImportBulkSupervisorRead,
)
def preview_import_supervisor_bulk(
    batch_id: UUID, payload: LogbookImportBulkSupervisorIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return excel_import.bulk_supervisor(db, batch_id, payload, current, apply=False)


@router.patch(
    "/logbook-import-batches/{batch_id}/supervisor",
    response_model=LogbookImportBulkSupervisorRead,
)
def update_import_supervisor_bulk(
    batch_id: UUID, payload: LogbookImportBulkSupervisorIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return excel_import.bulk_supervisor(db, batch_id, payload, current, apply=True)


@router.get("/logbook-instances/{instance_id}/materialized-items", response_model=list[InstanceItemRead])
def materialized_logbook_items(instance_id: UUID, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.list_items(db, instance_id, current)


@router.get("/logbook-instances/{instance_id}/daily-metrics", response_model=DailyMetricsRead)
def daily_logbook_metrics(instance_id: UUID, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.metrics(db, instance_id, current)


@router.post("/logbook-instance-items/{item_id}/my-contributions", response_model=ContributionRead, status_code=201)
def create_my_contribution(item_id: UUID, payload: ContributionIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.create(db, item_id, payload, current)


@router.patch("/logbook-contributions/{contribution_id}", response_model=ContributionRead)
def update_my_contribution(contribution_id: UUID, payload: ContributionIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.update(db, contribution_id, payload, current)


@router.put("/logbook-instance-items/{item_id}/my-contribution", response_model=ContributionRead, deprecated=True)
def save_my_contribution(item_id: UUID, payload: ContributionIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.save(db, item_id, payload, current)


@router.delete("/logbook-contributions/{contribution_id}", status_code=204)
def delete_my_contribution(contribution_id: UUID, version: int = Query(..., ge=1), db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    contributions.remove(db, contribution_id, version, current)
    return Response(status_code=204)


@router.post("/logbook-contributions/{contribution_id}/evidences", response_model=ContributionEvidenceRead, status_code=201)
def upload_contribution_evidence(contribution_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.upload_evidence(db, contribution_id, file, current)


@router.get("/logbook-contribution-evidences/{evidence_id}/access", response_model=EvidenceAccess)
def contribution_evidence_access(evidence_id: UUID, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return contributions.evidence_access(db, evidence_id, current)


@router.get("/logbook-contribution-evidences/{evidence_id}/content")
def contribution_evidence_content(evidence_id: UUID, token: str, db: Session = Depends(get_db)):
    content, content_type, filename = contributions.evidence_content(db, evidence_id, token)
    return Response(content=content, media_type=content_type, headers={"Content-Disposition": f'inline; filename="{filename}"', "Cache-Control": "private, no-store"})


@router.delete("/logbook-contribution-evidences/{evidence_id}", status_code=204)
def delete_contribution_evidence(evidence_id: UUID, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    contributions.delete_evidence(db, evidence_id, current)
    return Response(status_code=204)


@router.post("/logbook-recurrences/preview", response_model=RecurrencePreviewRead)
def preview_recurrence(
    payload: RecurrencePreviewIn,
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPERVISOR)),
):
    return recurrence.preview(payload)


@router.post("/events/{event_id}/logbook-recurrences", response_model=RecurrenceSeriesRead, status_code=201)
def create_recurrence(
    event_id: UUID, payload: RecurrenceSeriesCreate, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return recurrence.create_series(db, event_id, payload, current)


@router.get("/events/{event_id}/logbook-recurrences", response_model=list[RecurrenceSeriesRead])
def event_recurrences(
    event_id: UUID, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return recurrence.list_series(db, event_id, current)


@router.get("/logbook-recurrences/{series_id}", response_model=RecurrenceSeriesRead)
def recurrence_detail(
    series_id: UUID, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return recurrence.get_series(db, series_id, current)


@router.patch("/logbook-recurrences/{series_id}", response_model=RecurrenceSeriesRead)
def update_recurrence(
    series_id: UUID, payload: RecurrenceSeriesUpdate, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return recurrence.update_future(db, series_id, payload, current)


@router.get("/logbook-recurrences/{series_id}/occurrences", response_model=list[InstanceRead])
def recurrence_occurrences(
    series_id: UUID, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return recurrence.list_occurrences(db, series_id, current)


@router.post("/logbook-recurrences/{series_id}/pause", response_model=RecurrenceSeriesRead)
def pause_recurrence(series_id: UUID, payload: RecurrenceStatusIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return recurrence.set_status(db, series_id, LogbookRecurrenceStatus.PAUSED, current, payload.reason)


@router.post("/logbook-recurrences/{series_id}/resume", response_model=RecurrenceSeriesRead)
def resume_recurrence(series_id: UUID, payload: RecurrenceStatusIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return recurrence.set_status(db, series_id, LogbookRecurrenceStatus.ACTIVE, current, payload.reason)


@router.post("/logbook-recurrences/{series_id}/finish", response_model=RecurrenceSeriesRead)
def finish_recurrence(series_id: UUID, payload: RecurrenceStatusIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return recurrence.set_status(db, series_id, LogbookRecurrenceStatus.FINISHED, current, payload.reason)


@router.post("/logbook-recurrences/{series_id}/skip", response_model=RecurrenceSeriesRead)
def skip_recurrence_occurrence(series_id: UUID, payload: RecurrenceOccurrenceOperation, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return recurrence.skip_occurrence(db, series_id, payload, current)


@router.post("/logbook-recurrences/{series_id}/reschedule", response_model=InstanceRead)
def reschedule_recurrence_occurrence(series_id: UUID, payload: RecurrenceRescheduleIn, db: Session = Depends(get_db), current: User = Depends(get_current_active_user)):
    return recurrence.reschedule_occurrence(db, series_id, payload, current)


@router.post("/logbook-recurrences/{series_id}/generate", response_model=dict)
def generate_recurrence_window(
    series_id: UUID, db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    detail = recurrence.get_series(db, series_id, current)
    return recurrence.generate_series_window(db, detail["id"], actor=current)


@router.post(
    "/admin/logbooks/lifecycle/process",
    response_model=LifecycleProcessRead,
    summary="Procesar apertura y vencimiento de bitácoras",
)
def process_lifecycle(
    payload: LifecycleProcessIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    from app.services.logbook_lifecycle_service import process_logbook_lifecycle

    return process_logbook_lifecycle(
        db,
        batch_size=payload.batch_size,
        dry_run=payload.dry_run,
        actor=current,
        origin="MANUAL_ADMIN",
    )


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


@router.get("/me/logbooks", response_model=list[MyAssignmentRead])
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


@router.delete(
    "/logbook-assignments/{assignment_id}/responses/{item_id}",
    response_model=ResponseRead,
)
def clear_response(
    assignment_id: UUID,
    item_id: UUID,
    version: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    return service.clear_response(db, assignment_id, item_id, version, current)


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


@router.post(
    "/logbook-instances/{instance_id}/configuration/preview",
    response_model=InstanceConfigurationRead,
)
def preview_instance_configuration(
    instance_id: UUID, payload: InstanceConfigurationIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return service.configure_instance(db, instance_id, payload, current, apply=False)


@router.patch(
    "/logbook-instances/{instance_id}/configuration",
    response_model=InstanceConfigurationRead,
)
def update_instance_configuration(
    instance_id: UUID, payload: InstanceConfigurationIn,
    db: Session = Depends(get_db), current: User = Depends(get_current_active_user),
):
    return service.configure_instance(db, instance_id, payload, current, apply=True)


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
