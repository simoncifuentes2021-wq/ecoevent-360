"""Immutable publication workflow for builder reports."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import re
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import Report, ReportPublication, User
from app.models.enums import ReportPublicationStatus, ReportStatus, UserRole
from app.services import file_storage_service, report_pdf_service, report_revision_service
from app.services.report_render_service import ReportRenderDocument, evidence_asset, theme_for_template


def _admin(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(403, "Insufficient role")


def _report(db: Session, report_id: UUID, user: User) -> Report:
    from app.services import report_builder_service

    return report_builder_service.get_editor(db, report_id, user)


def prepare_document(
    report: Report, *, publication_number: int | None = None
) -> tuple[ReportRenderDocument, dict]:
    if len(report.sections) > 50 or len(report.evidences) > 100:
        raise HTTPException(413, "Report exceeds rendering limits")
    snapshot = report_revision_service.snapshot(report)
    event = report.event
    client = event.client
    section_key = {section.id: section.section_key for section in report.sections}
    evidences = []
    for item in sorted(report.evidences, key=lambda value: value.sort_order):
        if not item.is_enabled:
            continue
        uri, warning = evidence_asset(item.evidence.file_url, item.evidence.file_type)
        evidences.append(
            {
                "evidence_id": str(item.evidence_id),
                "section_key": section_key.get(item.section_id),
                "caption": item.caption or item.evidence.description,
                "uri": uri,
                "warning": warning,
            }
        )
    theme = theme_for_template(report.template_key.value, report.theme)
    document = ReportRenderDocument(
        report={
            "id": str(report.id),
            "title": report.title,
            "scope": report.scope.value,
            "template_key": report.template_key.value,
        },
        event={
            "id": str(event.id),
            "name": event.name,
            "date": f"{event.start_date:%d.%m.%Y} — {event.end_date:%d.%m.%Y}",
        },
        show={"id": str(report.session.id), "name": report.session.name}
        if report.session
        else None,
        client={"id": str(client.id), "name": client.business_name},
        theme=theme,
        sections=tuple(sorted(snapshot["sections"], key=lambda value: value["sort_order"])),
        evidences=tuple(evidences),
        publication={"number": publication_number, "generated_at": datetime.utcnow().isoformat()},
        editorial_config=report.editorial_config or {},
    )
    frozen = {
        **snapshot,
        "event": document.event,
        "show": document.show,
        "client": document.client,
        "theme": theme,
        "evidences_resolved": [{k: v for k, v in item.items() if k != "uri"} for item in evidences],
    }
    from app.services.report_page_planner import plan_pages

    frozen["page_plan"] = [
        page.as_dict()
        for page in plan_pages(snapshot["sections"], report.template_key.value, report.editorial_config)
    ]
    return document, frozen


def preview(db: Session, report_id: UUID, user: User) -> tuple[bytes, int, Report]:
    _admin(user)
    report = _report(db, report_id, user)
    document, _ = prepare_document(report)
    pdf, pages = report_pdf_service.render(document)
    return pdf, pages, report


def generate(db: Session, report_id: UUID, user: User, idempotency_key: str) -> ReportPublication:
    _admin(user)
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,100}", idempotency_key):
        raise HTTPException(422, "Invalid idempotency key")
    db.execute(select(Report.id).where(Report.id == report_id).with_for_update())
    existing = db.scalar(
        select(ReportPublication).where(
            ReportPublication.report_id == report_id,
            ReportPublication.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing
    report = _report(db, report_id, user)
    number = (
        db.scalar(
            select(func.max(ReportPublication.publication_number)).where(
                ReportPublication.report_id == report.id
            )
        )
        or 0
    ) + 1
    document, frozen = prepare_document(report, publication_number=number)
    pdf, pages = report_pdf_service.render(document)
    digest = sha256(pdf).hexdigest()
    key = f"{file_storage_service.settings.r2_private_prefix.strip('/')}/reports/{report.event_id}/{report.id}/publications/v{number}/report-{digest[:12]}.pdf"
    try:
        file_storage_service.save_private_object(key, pdf, content_type="application/pdf")
        publication = ReportPublication(
            report_id=report.id,
            publication_number=number,
            status=ReportPublicationStatus.GENERATED,
            storage_key=key,
            sha256=digest,
            file_size=len(pdf),
            page_count=pages,
            snapshot=frozen,
            theme_snapshot=document.theme,
            generated_by=user.id,
            idempotency_key=idempotency_key,
        )
        db.add(publication)
        report.status = ReportStatus.GENERATED
        report.generated_by = user.id
        report.generated_at = datetime.utcnow()
        db.commit()
        db.refresh(publication)
        return publication
    except Exception as exc:
        db.rollback()
        try:
            file_storage_service.delete_stored_file(key)
        except Exception:
            # A storage outage must not replace the original upload error.
            pass
        raise HTTPException(
            502,
            "No se pudo guardar el PDF. Revisa la configuración del almacenamiento privado.",
        ) from exc


def list_publications(db: Session, report_id: UUID, user: User) -> list[ReportPublication]:
    report = _report(db, report_id, user)
    query = select(ReportPublication).where(ReportPublication.report_id == report.id)
    if user.role == UserRole.CLIENT:
        query = query.where(ReportPublication.status == ReportPublicationStatus.DELIVERED)
    return list(db.scalars(query.order_by(ReportPublication.publication_number.desc())).all())


def get_publication(db: Session, publication_id: UUID, user: User) -> ReportPublication:
    publication = db.scalar(
        select(ReportPublication)
        .options(selectinload(ReportPublication.report))
        .where(ReportPublication.id == publication_id)
    )
    if not publication:
        raise HTTPException(404, "Publication not found")
    from app.services.report_service import _ensure_can_access_event

    _ensure_can_access_event(db, user, publication.report.event_id)
    if user.role == UserRole.CLIENT and publication.status != ReportPublicationStatus.DELIVERED:
        raise HTTPException(404, "Publication not found")
    return publication


def deliver(db: Session, publication_id: UUID, user: User) -> ReportPublication:
    _admin(user)
    item = get_publication(db, publication_id, user)
    if item.status == ReportPublicationStatus.ARCHIVED:
        raise HTTPException(409, "Archived publication cannot be delivered")
    item.status = ReportPublicationStatus.DELIVERED
    item.delivered_by = user.id
    item.delivered_at = datetime.utcnow()
    item.report.status = ReportStatus.DELIVERED
    item.report.delivered_at = item.delivered_at
    db.commit()
    db.refresh(item)
    return item


def archive(db: Session, publication_id: UUID, user: User) -> ReportPublication:
    _admin(user)
    item = get_publication(db, publication_id, user)
    if item.status == ReportPublicationStatus.DELIVERED:
        raise HTTPException(409, "Delivered publication cannot be archived")
    item.status = ReportPublicationStatus.ARCHIVED
    db.commit()
    db.refresh(item)
    return item
