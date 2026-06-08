from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.report_schema import ReportListResponse, ReportRead
from app.services import report_service
from app.services.audit_log_service import create_audit_log, serialize_model_for_audit

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return report_service.ensure_can_access_report(db, current_user, report_id)


@router.get("/{report_id}/download")
def download_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    report = report_service.ensure_can_access_report(db, current_user, report_id)
    buffer = report_service.build_report_pdf(report)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_DOWNLOADED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        status="SUCCESS",
        metadata={"filename": f"report-{report.id}.pdf"},
        request=request,
    )
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
    )


@router.patch("/{report_id}/deliver", response_model=ReportRead)
def mark_report_delivered(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = report_service.ensure_can_access_report(db, current_user, report_id)
    old_data = serialize_model_for_audit(before)
    report = report_service.mark_report_delivered(db, report_id=report_id, current_user=current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_DELIVERED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        old_data=old_data,
        new_data=serialize_model_for_audit(report),
        request=request,
    )
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    before = report_service.ensure_can_access_report(db, current_user, report_id)
    report = report_service.archive_report(db, report_id=report_id, current_user=current_user)
    create_audit_log(
        db,
        user=current_user,
        action="REPORT_ARCHIVED",
        module="reports",
        entity_type="Report",
        entity_id=report.id,
        event_id=report.event_id,
        old_data=serialize_model_for_audit(before),
        new_data=serialize_model_for_audit(report),
        request=request,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/events/{event_id}/pdf")
def event_report_pdf(event_id: int, request: Request, db: Session = Depends(get_db)):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(f"EcoEvent 360 Reporte Evento {event_id}")
    pdf.drawString(72, 740, "EcoEvent 360")
    pdf.drawString(72, 710, f"Reporte operacional y ambiental del evento #{event_id}")
    pdf.drawString(72, 680, "Resumen generado desde datos registrados en la plataforma.")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    create_audit_log(
        db,
        action="REPORT_DOWNLOADED",
        module="reports",
        entity_type="Report",
        status="SUCCESS",
        metadata={"legacy_event_id": event_id, "filename": f"event-{event_id}-report.pdf"},
        request=request,
    )
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="event-{event_id}-report.pdf"'},
    )
