from datetime import datetime
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, status
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event
from app.models.core import Event, Report, User
from app.models.enums import ReportStatus, UserRole


def _ensure_can_access_event(db: Session, user: User, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return event


def _ensure_admin(user: User) -> None:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def get_report_or_404(db: Session, report_id: UUID) -> Report:
    report = db.scalar(
        select(Report)
        .options(selectinload(Report.event))
        .where(Report.id == report_id, Report.status != ReportStatus.ARCHIVED)
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def ensure_can_access_report(db: Session, user: User, report_id: UUID) -> Report:
    report = get_report_or_404(db, report_id)
    _ensure_can_access_event(db, user, report.event_id)
    return report


def list_event_reports(
    db: Session,
    *,
    event_id: UUID,
    current_user: User,
    page: int,
    limit: int,
) -> tuple[list[Report], int]:
    _ensure_can_access_event(db, current_user, event_id)
    filters = [Report.event_id == event_id, Report.status != ReportStatus.ARCHIVED]

    total = db.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Report)
            .options(selectinload(Report.event))
            .where(*filters)
            .order_by(Report.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return items, total


def create_final_report(db: Session, *, event_id: UUID, current_user: User) -> Report:
    _ensure_admin(current_user)
    event = _ensure_can_access_event(db, current_user, event_id)
    report = Report(
        event_id=event.id,
        title=f"Reporte final - {event.name}",
        summary="Reporte operacional y ambiental generado desde los datos registrados del evento.",
        status=ReportStatus.GENERATED,
        generated_by=current_user.id,
        generated_at=datetime.utcnow(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def mark_report_delivered(db: Session, *, report_id: UUID, current_user: User) -> Report:
    _ensure_admin(current_user)
    report = get_report_or_404(db, report_id)
    report.status = ReportStatus.DELIVERED
    report.delivered_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report


def archive_report(db: Session, *, report_id: UUID, current_user: User) -> Report:
    _ensure_admin(current_user)
    report = get_report_or_404(db, report_id)
    report.status = ReportStatus.ARCHIVED
    db.commit()
    db.refresh(report)
    return report


def build_report_pdf(report: Report) -> BytesIO:
    event = report.event
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle(report.title)
    pdf.drawString(72, 740, "EcoEvent 360")
    pdf.drawString(72, 710, report.title)
    pdf.drawString(72, 680, f"Evento: {event.name if event else report.event_id}")
    if event:
        pdf.drawString(72, 650, f"Ubicacion: {event.location_name or event.city or 'No registrada'}")
        pdf.drawString(72, 620, f"Fechas: {event.start_date.date()} - {event.end_date.date()}")
        pdf.drawString(72, 590, f"Estado: {event.status.value}")
    pdf.drawString(72, 550, report.summary or "Resumen generado desde datos registrados en la plataforma.")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
