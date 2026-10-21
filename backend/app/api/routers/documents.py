import hashlib
import re
import time
import unicodedata
from urllib.parse import quote
from threading import Lock
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.core.permissions import can_view_operational_event
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.core import Event, User
from app.models.enums import UserRole
from app.models.documents import DocumentEmployment, DocumentPerson, ManagedDocument
from app.schemas.document_schema import (
    DocumentCreate,
    DocumentBatchRetry,
    DocumentBatchSendCreate,
    DocumentContractDefaults,
    DocumentSendTogether,
    DocumentUpdate,
    EventEppTemplateUpdate,
    ExistingPeopleAssignmentCommit,
    EmploymentUpdate,
    GenerateMissingDraftsCommit,
    PaperBatchPrintRequest,
    PersonCreate,
    PersonImportCommit,
    PersonUpdate,
    RepresentativeSignatureSave,
    PublicDocumentOpen,
    PublicDocumentPreview,
    PublicDocumentSign,
)
from app.services import (
    document_batch_service,
    document_people_service,
    document_reporting_service,
    document_email_queue_service,
    managed_documents_service,
)
from app.services.audit_log_service import create_audit_log

router = APIRouter(prefix="/documents", tags=["documents"])
_staff_roles = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPERVISOR)
_rate_limit_counts: dict[tuple[str, int], int] = {}
_rate_limit_lock = Lock()


@router.post("/events/{event_id}/paper-print-batch")
def print_paper_batch(
    event_id: UUID,
    payload: PaperBatchPrintRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    content, batch = managed_documents_service.build_paper_print_batch(
        db, event_id, payload.person_ids, payload.kinds, current_user
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_PAPER_PRINT_BATCH_PREPARED",
        event_id=event_id,
        request=request,
        metadata={
            "people_count": len(set(payload.person_ids)),
            "document_count": batch.document_count,
            "page_count": batch.page_count,
            "batch_id": str(batch.id),
            "kinds": payload.kinds,
        },
        entity_id=batch.id,
        entity_type="DocumentPaperBatch",
    )
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="greenway-firma-papel-{event_id}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Documents-Included": str(batch.document_count),
            "X-Pages": str(batch.page_count),
            "X-Paper-Batch-Id": str(batch.id),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{document_id}/paper-print")
def print_single_paper_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    document = db.get(ManagedDocument, document_id)
    if not document or not document.event_id:
        raise HTTPException(status_code=404, detail="Documento de faena no encontrado")
    content, batch = managed_documents_service.build_paper_print_batch(
        db,
        document.event_id,
        [document.person_id],
        [document.kind],
        current_user,
        document_ids=[document.id],
        allow_reprint_existing=True,
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_PAPER_PRINT_SINGLE_PREPARED",
        document_id=document.id,
        event_id=document.event_id,
        request=request,
        metadata={"batch_id": str(batch.id), "document_version": document.version},
        entity_id=batch.id,
        entity_type="DocumentPaperBatch",
    )
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="greenway-papel-{document.id}-v{document.version}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Documents-Included": str(batch.document_count),
            "X-Pages": str(batch.page_count),
            "X-Paper-Batch-Id": str(batch.id),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/events/{event_id}/paper-batches")
def get_paper_batches(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return managed_documents_service.list_paper_batches(db, event_id, current_user)


@router.get("/paper-batches/{batch_id}/pdf")
def download_paper_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    content, batch = managed_documents_service.get_paper_batch(db, batch_id, current_user)
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="greenway-papel-{batch.id}.pdf"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


@router.post("/paper-batches/{batch_id}/printed")
def mark_paper_batch_printed(
    batch_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.mark_paper_batch_printed(db, batch_id, current_user)
    _audit(db, current_user, "DOCUMENT_PAPER_BATCH_PRINTED", event_id=UUID(result["event_id"]), request=request, metadata={"batch_id": str(batch_id), "documents": result["document_count"]}, entity_id=batch_id, entity_type="DocumentPaperBatch")
    return result


@router.post("/{document_id}/paper-signed-received")
def mark_paper_signed_received(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.mark_paper_document_signed_received(db, document_id, current_user)
    _audit(db, current_user, "DOCUMENT_PAPER_SIGNED_RECEIVED", document_id, result.get("event_id"), request, {"paper_status": result["paper_status"]})
    return result


@router.post("/{document_id}/paper-signed-copy", status_code=200)
def upload_paper_signed_copy(
    document_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    content = file.file.read(settings.max_upload_size_bytes + 1)
    result = managed_documents_service.upload_paper_signed_copy(
        db, document_id, current_user, content, file.content_type or "", file.filename or "copia-firmada"
    )
    _audit(db, current_user, "DOCUMENT_PAPER_SIGNED_COPY_ARCHIVED", document_id, result.get("event_id"), request, {"sha256": result.get("paper_evidence_sha256"), "file_name": result.get("paper_evidence_file_name")})
    return result


@router.get("/{document_id}/paper-signed-copy")
def download_paper_signed_copy(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    content, mime, filename = managed_documents_service.download_paper_signed_copy(db, document_id, current_user)
    disposition = "inline" if mime == "application/pdf" else "attachment"
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f'{disposition}; filename="{quote(filename)}"',
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
    })


@router.get("/contract-defaults")
def get_contract_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return managed_documents_service.get_contract_defaults(db)


@router.get("/events/{event_id}/contract-defaults")
def get_event_contract_defaults(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    event = db.get(Event, event_id)
    if not event or not can_view_operational_event(current_user, event, db):
        raise HTTPException(status_code=404, detail="Faena no encontrada o sin acceso")
    return managed_documents_service.get_event_contract_defaults(db, event_id)


@router.put("/events/{event_id}/contract-defaults")
def save_event_contract_defaults(
    event_id: UUID,
    payload: DocumentContractDefaults,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.save_event_contract_defaults(db, event_id, payload, current_user)
    _audit(db, current_user, "DOCUMENT_EVENT_CONTRACT_DEFAULTS_UPDATED", event_id=event_id, request=request)
    return result


@router.post("/events/{event_id}/apply-employer-defaults-to-drafts")
def apply_employer_defaults_to_drafts(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.apply_employer_defaults_to_drafts(
        db, event_id, current_user
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_EMPLOYER_DEFAULTS_APPLIED_TO_DRAFTS",
        event_id=event_id,
        request=request,
        metadata={
            "documents_checked": result["documents_checked"],
            "documents_updated": result["documents_updated"],
            "fields_filled": result["fields_filled"],
        },
        entity_id=event_id,
        entity_type="Event",
    )
    return result


@router.delete("/events/{event_id}/contract-defaults")
def reset_event_contract_defaults(
    event_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.clear_event_contract_defaults(db, event_id, current_user)
    _audit(db, current_user, "DOCUMENT_EVENT_CONTRACT_DEFAULTS_RESET", event_id=event_id, request=request)
    return result


@router.get("/events/{event_id}/status.xlsx")
def export_event_document_status(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    event = db.get(Event, event_id)
    content = document_reporting_service.build_event_document_status_xlsx(
        db, event_id, current_user
    )
    name = unicodedata.normalize("NFD", event.name if event else "faena")
    name = re.sub(r"[^a-zA-Z0-9]+", "-", "".join(char for char in name if not unicodedata.combining(char))).strip("-").lower()
    filename = f"estado-documentos-{name or 'faena'}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/events/{event_id}/epp-template")
def get_event_epp_template(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return managed_documents_service.get_event_epp_template(db, event_id, current_user)


@router.put("/events/{event_id}/epp-template")
def save_event_epp_template(
    event_id: UUID,
    payload: EventEppTemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.save_event_epp_template(db, event_id, payload, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_EVENT_EPP_TEMPLATE_UPDATED",
        event_id=event_id,
        request=request,
        metadata={"item_count": len(result["items"])},
        entity_id=event_id,
    )
    return result


@router.put("/contract-defaults")
def save_contract_defaults(
    payload: DocumentContractDefaults,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.save_contract_defaults(db, payload, current_user)
    _audit(db, current_user, "DOCUMENT_CONTRACT_DEFAULTS_UPDATED", request=request)
    return result


@router.get("/representative-signature")
def get_representative_signature(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    return managed_documents_service.get_representative_signature(db, current_user)


@router.put("/representative-signature")
def save_representative_signature(
    payload: RepresentativeSignatureSave,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.save_representative_signature(db, payload, current_user)
    _audit(db, current_user, "DOCUMENT_REPRESENTATIVE_SIGNATURE_UPDATED", request=request)
    return result


@router.delete("/representative-signature")
def delete_representative_signature(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = managed_documents_service.delete_representative_signature(db, current_user)
    _audit(db, current_user, "DOCUMENT_REPRESENTATIVE_SIGNATURE_DELETED", request=request)
    return result


def _enforce_local_public_limit(
    request: Request, bucket: str, token_digest: str, limit: int
) -> None:
    peer = request.client.host if request.client else "unknown"
    identity = hashlib.sha256(f"{peer}:{token_digest}".encode("utf-8")).hexdigest()
    now = int(time.time())
    window = now // 300
    key = (f"{bucket}:{identity}", window)
    with _rate_limit_lock:
        if len(_rate_limit_counts) > 10_000:
            for old_key in tuple(_rate_limit_counts):
                if old_key[1] < window - 1:
                    del _rate_limit_counts[old_key]
        count = _rate_limit_counts.get(key, 0) + 1
        _rate_limit_counts[key] = count
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Vuelve a intentarlo más tarde.",
            headers={"Retry-After": str(300 - now % 300)},
        )


def _audit(
    db: Session,
    user: User,
    action: str,
    document_id: UUID | None = None,
    event_id: UUID | None = None,
    request: Request | None = None,
    metadata: dict | None = None,
    *,
    entity_id: UUID | None = None,
    entity_type: str | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> None:
    create_audit_log(
        db,
        user=user,
        action=action,
        module="documents",
        entity_type=entity_type or ("ManagedDocument" if document_id else "DocumentPerson"),
        entity_id=document_id or entity_id,
        event_id=event_id,
        metadata=metadata or {},
        old_data=old_data,
        new_data=new_data,
        request=request,
    )


@router.get("/people/template")
def download_people_template(
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    content = document_people_service.excel_template()
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="greenway-personas.xlsx"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/people/import/preview")
async def preview_people_import(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Sube un archivo Excel .xlsx")
    content = await file.read(document_people_service.MAX_IMPORT_BYTES + 1)
    await file.close()
    return document_people_service.preview_import(content)


@router.post("/people/import")
def commit_people_import(
    payload: PersonImportCommit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = document_people_service.commit_import(db, payload, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_PEOPLE_IMPORTED",
        request=request,
        metadata={
            "created_count": result["created"],
            "updated_count": result["updated"],
            "assignment_count": result["assignments"],
        },
    )
    for row in result["results"]:
        if row.get("person_id") and row.get("status") == "SUCCESS":
            create_audit_log(
                db, user=current_user, action="DOCUMENT_PERSON_IMPORTED", module="documents",
                entity_type="DocumentPerson", entity_id=UUID(row["person_id"]),
                event_id=payload.event_id, request=request,
                metadata={"person_action": row["person_action"], "assignment_action": row["assignment_action"], "rut": row["rut"]},
            )
    return result


@router.post("/people/import-and-generate")
def import_people_and_generate_documents(
    payload: PersonImportCommit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = document_batch_service.generate_draft_pairs(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="DOCUMENT_BATCH_DRAFTS_GENERATED",
        module="documents",
        event_id=payload.event_id,
        request=request,
        metadata={
            "workers_processed": result["workers_processed"],
            "documents_created": result["documents_created"],
            "documents_skipped": result["documents_skipped"],
        },
    )
    for row in result["results"]:
        if row.get("person_id") and row.get("status") == "SUCCESS":
            create_audit_log(
                db, user=current_user, action="DOCUMENT_BATCH_WORKER_PROCESSED", module="documents",
                entity_type="DocumentPerson", entity_id=UUID(row["person_id"]),
                event_id=payload.event_id, request=request,
                metadata={"created": row["created"], "already_had": row["already_had"], "rut": row["rut"]},
            )
    return result


@router.post("/people/import-and-generate/preview")
def preview_import_and_generate_documents(
    payload: PersonImportCommit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return document_batch_service.preview_import_draft_pairs(db, payload, current_user)


@router.post("/events/preview-missing-drafts")
def preview_missing_event_drafts(
    payload: GenerateMissingDraftsCommit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return document_batch_service.preview_missing_draft_pairs(db, payload, current_user)


@router.post("/events/generate-missing-drafts")
def generate_missing_event_drafts(
    payload: GenerateMissingDraftsCommit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = document_batch_service.generate_missing_draft_pairs(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="DOCUMENT_MISSING_DRAFTS_GENERATED",
        module="documents",
        event_id=payload.event_id,
        request=request,
        metadata={
            "workers_processed": result["workers_processed"],
            "documents_created": result["documents_created"],
            "documents_skipped": result["documents_skipped"],
        },
    )
    for row in result["results"]:
        if row.get("person_id"):
            create_audit_log(
                db, user=current_user, action="DOCUMENT_MISSING_DRAFTS_WORKER_PROCESSED", module="documents",
                entity_type="DocumentPerson", entity_id=UUID(row["person_id"]),
                event_id=payload.event_id, request=request,
                metadata={"created": row["created"], "already_had": row["already_had"], "rut": row["rut"]},
            )
    return result


@router.post("/people/assign-existing")
def assign_existing_people(
    payload: ExistingPeopleAssignmentCommit,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    result = document_batch_service.assign_existing_people(db, payload, current_user)
    create_audit_log(
        db,
        user=current_user,
        action="DOCUMENT_EXISTING_PEOPLE_ASSIGNED",
        module="documents",
        event_id=payload.target_event_id,
        request=request,
        metadata={
            "source_event_id": str(payload.source_event_id),
            "assigned_count": len(result["assigned"]),
            "already_assigned_count": len(result["already_assigned"]),
            "documents_created": result["documents_created"],
        },
    )
    return result


@router.get("/people")
def list_people(
    q: str | None = Query(default=None, max_length=120),
    event_id: UUID | None = None,
    client_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return document_people_service.list_people(
        db, current_user, q=q, event_id=event_id, client_id=client_id
    )


@router.get("/people/{person_id}/history")
def get_person_document_history(
    person_id: UUID,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    person = db.get(DocumentPerson, person_id)
    event = db.get(Event, event_id)
    if not person or not event or not can_view_operational_event(current_user, event, db):
        raise HTTPException(status_code=404, detail="Persona o faena no encontrada")
    assignment_ids = list(db.scalars(select(DocumentEmployment.id).where(
        DocumentEmployment.person_id == person_id,
        DocumentEmployment.event_id == event_id,
    )).all())
    if not assignment_ids:
        raise HTTPException(status_code=404, detail="La persona no pertenece a esta faena")
    document_ids = list(db.scalars(select(ManagedDocument.id).where(
        ManagedDocument.person_id == person_id,
        ManagedDocument.event_id == event_id,
    )).all())
    entity_ids = {person_id, *assignment_ids, *document_ids}
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(
            AuditLog.module == "documents",
            AuditLog.entity_id.in_(entity_ids),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()
    return [{
        "id": str(log.id),
        "action": log.action,
        "description": log.description,
        "actor": actor or "Usuario del sistema",
        "created_at": log.created_at,
        "old_data": log.old_data,
        "new_data": log.new_data,
        "metadata": log.metadata_,
    } for log, actor in rows]


@router.post("/people", status_code=201)
def create_person(
    payload: PersonCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    person = document_people_service.create_person(db, payload, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_PERSON_CREATED",
        request=request,
        metadata={"person_id": str(person.id), "event_id": str(payload.employment.event_id)},
        entity_id=person.id,
    )
    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "rut": person.rut,
        "email": person.email,
        "phone": person.phone,
        "address": person.address,
        "commune": person.commune,
        "updated_at": person.updated_at,
        "latest_employment": None,
    }


@router.patch("/people/{person_id}")
def update_person(
    person_id: UUID,
    payload: PersonUpdate,
    request: Request,
    event_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    before = db.get(DocumentPerson, person_id)
    old_data = ({
        "first_name": before.first_name, "last_name": before.last_name, "rut": before.rut,
        "email": before.email, "phone": before.phone, "address": before.address, "commune": before.commune,
    } if before else None)
    person = document_people_service.update_person(
        db, person_id, payload, current_user, event_id=event_id
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_PERSON_UPDATED",
        request=request,
        metadata={"person_id": str(person.id), "event_id": str(event_id) if event_id else None},
        entity_id=person.id,
        old_data=old_data,
        new_data={
            "first_name": person.first_name, "last_name": person.last_name, "rut": person.rut,
            "email": person.email, "phone": person.phone, "address": person.address, "commune": person.commune,
        },
    )
    return {
        "id": person.id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "rut": person.rut,
        "email": person.email,
        "phone": person.phone,
        "address": person.address,
        "commune": person.commune,
        "updated_at": person.updated_at,
        "latest_employment": None,
    }


@router.patch("/people/{person_id}/employments/{employment_id}")
def update_person_employment(
    person_id: UUID,
    employment_id: UUID,
    payload: EmploymentUpdate,
    request: Request,
    event_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    before = db.get(DocumentEmployment, employment_id)
    old_data = ({
        "position": before.position, "area": before.area, "workplace": before.workplace,
        "start_date": before.start_date.isoformat() if before.start_date else None,
        "end_date": before.end_date.isoformat() if before.end_date else None,
        "remuneration": str(before.remuneration) if before.remuneration is not None else None,
    } if before else None)
    assignment = document_people_service.update_employment(
        db,
        person_id,
        employment_id,
        payload,
        current_user,
        event_id=event_id,
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_EMPLOYMENT_UPDATED",
        request=request,
        metadata={"person_id": str(person_id), "event_id": str(assignment.event_id)},
        entity_id=assignment.id,
        entity_type="DocumentEmployment",
        old_data=old_data,
        new_data={
            "position": assignment.position, "area": assignment.area, "workplace": assignment.workplace,
            "start_date": assignment.start_date.isoformat() if assignment.start_date else None,
            "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
            "remuneration": str(assignment.remuneration) if assignment.remuneration is not None else None,
        },
    )
    return {
        "id": assignment.id,
        "person_id": assignment.person_id,
        "event_id": assignment.event_id,
        "position": assignment.position,
        "area": assignment.area,
        "workplace": assignment.workplace,
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "remuneration": str(assignment.remuneration) if assignment.remuneration is not None else None,
        "updated_at": assignment.updated_at,
    }


@router.get("/summary")
def get_document_summary(
    event_id: UUID | None = None,
    client_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return managed_documents_service.summary(
        db, current_user, event_id=event_id, client_id=client_id
    )


@router.get("/public/status")
def public_signing_provider_status():
    return {
        "provider": "LOCAL_SIMULATED",
        "legal_signature": False,
        "message": managed_documents_service.SIGNATURE_NOTICE,
    }


@router.post("/public/open")
def open_public_document(
    payload: PublicDocumentOpen,
    request: Request,
    db: Session = Depends(get_db),
):
    digest = managed_documents_service.token_digest(payload.token)
    _enforce_local_public_limit(request, "document_public_open", digest, 10)
    return managed_documents_service.open_public_document(db, payload.token, payload.rut)


@router.post("/public/sign")
def sign_public_document(
    payload: PublicDocumentSign,
    request: Request,
    db: Session = Depends(get_db),
):
    digest = managed_documents_service.token_digest(payload.token)
    _enforce_local_public_limit(request, "document_public_sign", digest, 5)
    return managed_documents_service.sign_public_document(
        db,
        payload.token,
        payload.rut,
        payload.worker_name,
        payload.accepted,
        payload.electronic_consent,
        payload.epp_acknowledgments,
        payload.worker_signature_data_url,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/public/preview")
def preview_public_document(
    payload: PublicDocumentPreview,
    request: Request,
    db: Session = Depends(get_db),
):
    digest = managed_documents_service.token_digest(payload.token)
    _enforce_local_public_limit(request, "document_public_preview", digest, 15)
    content = managed_documents_service.preview_public_document_pdf(db, payload.token, payload.rut)
    return Response(
        content, media_type="application/pdf", headers={"Cache-Control": "private, no-store"}
    )


@router.get("")
def list_documents(
    event_id: UUID | None = None,
    kind: str | None = None,
    document_status: str | None = Query(default=None, alias="status"),
    client_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return managed_documents_service.list_documents(
        db, current_user, event_id=event_id, kind=kind, status=document_status, client_id=client_id
    )


@router.post("", status_code=201)
def create_document(
    payload: DocumentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.create_document(db, payload, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_CREATED",
        result["id"],
        result["event_id"],
        request,
        {"kind": result["kind"], "status": result["status"]},
    )
    return result


@router.post("/{document_id}/signed-copy")
def resend_signed_document_copy(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.resend_signed_copy(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_SIGNED_COPY_SENT",
        document_id,
        None,
        request,
        {"recipient": result["recipient"], "email_sent": result["email_sent"]},
    )
    return result


@router.get("/{document_id}")
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return managed_documents_service.get_document(db, document_id, current_user)


@router.patch("/{document_id}")
def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    before = db.get(ManagedDocument, document_id)
    old_data = ({"title": before.title, "data": before.data, "status": before.status} if before else None)
    result = managed_documents_service.update_document(db, document_id, payload, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_UPDATED",
        document_id,
        result["event_id"],
        request,
        {"kind": result["kind"], "status": result["status"]},
        old_data=old_data,
        new_data={"title": result["title"], "data": result["data"], "status": result["status"]},
    )
    return result


@router.post("/{document_id}/preview")
def preview_document_pdf(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    content = managed_documents_service.preview_pdf(db, document_id, current_user)
    return Response(
        content, media_type="application/pdf", headers={"Cache-Control": "private, no-store"}
    )


@router.post("/{document_id}/prepare")
def prepare_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.prepare_document(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_PREPARED",
        document_id,
        result["event_id"],
        request,
        {"status": "READY"},
    )
    return result


@router.post("/{document_id}/send")
def send_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.send_for_signature(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_SENT_FOR_SIGNATURE",
        document_id,
        result["document"]["event_id"],
        request,
        {"status": "SENT"},
    )
    return result


@router.post("/send-together")
def send_documents_together(
    payload: DocumentSendTogether,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.send_documents_together(
        db, payload.contract_document_id, payload.epp_document_id, current_user
    )
    for document in result["documents"]:
        _audit(
            db,
            current_user,
            "DOCUMENT_SENT_WITH_CONTRACT_BUNDLE",
            document["id"],
            document.get("event_id"),
            request,
            {"recipient": result["recipient"], "email_sent": result["email_sent"]},
        )
    return result


@router.post("/send-together/batches")
def create_documents_email_batch(
    payload: DocumentBatchSendCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = document_email_queue_service.create_batch(
        db,
        batch_id=payload.batch_id,
        event_id=payload.event_id,
        pairs=payload.pairs,
        user=current_user,
    )
    _audit(
        db,
        current_user,
        "DOCUMENT_BULK_EMAIL_BATCH_QUEUED",
        event_id=payload.event_id,
        request=request,
        metadata={"total": result["total"], "skipped": result["skipped"]},
        entity_id=payload.batch_id,
        entity_type="DocumentEmailBatch",
    )
    return result


@router.get("/send-together/batches/{batch_id}")
def get_documents_email_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return document_email_queue_service.get_batch(db, batch_id, current_user)


@router.post("/send-together/batches/{batch_id}/retry")
def retry_documents_email_batch(
    batch_id: UUID,
    payload: DocumentBatchRetry,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    return document_email_queue_service.retry_failed(db, batch_id, payload.item_ids, current_user)


@router.post("/{document_id}/new-version", status_code=201)
def create_document_version(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.create_new_version(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_VERSION_CREATED",
        document_id,
        result["event_id"],
        request,
        {"new_document_id": str(result["id"]), "version": result["version"]},
    )
    return result


@router.post("/{document_id}/cancel")
def cancel_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.cancel_document(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_CANCELLED",
        document_id,
        result["event_id"],
        request,
        {"status": result["status"]},
    )
    return result


@router.post("/{document_id}/supervisor-sign")
def supervisor_sign_document(
    document_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_staff_roles)),
):
    result = managed_documents_service.supervisor_sign(db, document_id, current_user)
    _audit(
        db,
        current_user,
        "DOCUMENT_COMPLETED",
        document_id,
        result["event_id"],
        request,
        {"status": result["status"], "signature_provider": "LOCAL_SIMULATED"},
    )
    return result


@router.get("/{document_id}/pdf")
def download_document_pdf(
    document_id: UUID,
    signed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    content = managed_documents_service.download_document(
        db, document_id, current_user, signed=signed
    )
    suffix = "signed" if signed else "original"
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="document-{document_id}-{suffix}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
