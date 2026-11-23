from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.disposal_certificate_schema import (
    DisposalCertificateContext,
    DisposalCertificateCreate,
    DisposalCertificateRead,
    DisposalCertificateDefaultsUpdate,
)
from app.api.deps import require_roles
from app.models.enums import UserRole
from app.services import disposal_certificate_service as service
from app.services.audit_log_service import create_audit_log

router = APIRouter(tags=["waste disposal certificates"])


@router.put("/disposal-certificates/defaults")
def save_defaults(
    payload: DisposalCertificateDefaultsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    result = service.save_disposal_defaults(db, payload, user)
    create_audit_log(db, user=user, action="WASTE_DISPOSAL_CERTIFICATE_DEFAULTS_UPDATED", module="waste", entity_type="DocumentContractDefaults", request=request)
    return result


@router.get("/disposal-certificates/defaults")
def get_defaults(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    return service.get_disposal_defaults(db)


@router.get("/events/{event_id}/disposal-certificates/context", response_model=DisposalCertificateContext)
def get_context(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    return service.get_context(db, event_id, user)


@router.post("/events/{event_id}/disposal-certificates/preview")
def preview_certificate(
    event_id: UUID,
    payload: DisposalCertificateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    content = service.preview_certificate(db, event_id, user, payload)
    return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="certificado-vista-previa.pdf"', "Cache-Control": "private, no-store"})


@router.post("/events/{event_id}/disposal-certificates", response_model=DisposalCertificateRead, status_code=status.HTTP_201_CREATED)
def create_certificate(
    event_id: UUID,
    payload: DisposalCertificateCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    item = service.create_certificate(db, event_id, user, payload)
    result = service.list_item(item)
    result["file_size"] = item.file_size
    create_audit_log(
        db,
        user=user,
        action="ISSUE",
        module="waste",
        entity_type="WasteDisposalCertificate",
        entity_id=item.id,
        event_id=event_id,
        new_data={"certificate_number": item.certificate_number, "sha256": item.sha256, "total_kg": result["total_kg"], "receiving_facility_name": result["receiving_facility_name"]},
        request=request,
    )
    return result


@router.get("/disposal-certificates/{certificate_id}/pdf")
def download_certificate(certificate_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_active_user)):
    item, content = service.get_pdf(db, certificate_id, user)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{item.certificate_number}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Document-SHA256": item.sha256,
        },
    )
