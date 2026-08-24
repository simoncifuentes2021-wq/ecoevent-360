from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    Report,
    ReportElement,
    ReportEvidence,
    ReportLayoutOverride,
    ReportPage,
    ReportRevision,
    ReportSection,
    User,
)
from app.models.enums import ReportCompositionMode
from app.services.report_builder_service import _assert_editable


def snapshot(report: Report) -> dict:
    return {
        "title": report.title,
        "edit_version": report.edit_version,
        "summary": report.summary,
        "scope": report.scope.value,
        "session_id": str(report.session_id) if report.session_id else None,
        "template_key": report.template_key.value,
        "theme": report.theme,
        "editorial_config": report.editorial_config,
        "composition_mode": report.composition_mode.value,
        "layout_overrides": [
            {
                "element_key": item.element_key,
                "page_key": item.page_key,
                "x_offset": item.x_offset,
                "y_offset": item.y_offset,
                "width_scale": item.width_scale,
                "height_scale": item.height_scale,
                "rotation": item.rotation,
                "z_index": item.z_index,
                "locked": item.locked,
                "visible": item.visible,
            }
            for item in report.layout_overrides
        ],
        "pages": [
            {
                "id": str(page.id),
                "page_number": page.page_number,
                "name": page.name,
                "width": page.width,
                "height": page.height,
                "background": page.background,
                "background_image": page.background_image,
                "is_enabled": page.is_enabled,
                "elements": [
                    {
                        "id": str(element.id),
                        "type": element.type.value,
                        "x": element.x,
                        "y": element.y,
                        "width": element.width,
                        "height": element.height,
                        "rotation": element.rotation,
                        "z_index": element.z_index,
                        "locked": element.locked,
                        "visible": element.visible,
                        "content": element.content,
                        "style": element.style,
                        "data_binding": element.data_binding,
                        "metadata": element.metadata_,
                    }
                    for element in page.elements
                ],
            }
            for page in report.pages
        ],
        "sections": [
            {
                "section_key": s.section_key,
                "section_type": s.section_type.value,
                "title": s.title,
                "layout_variant": s.layout_variant.value,
                "is_enabled": s.is_enabled,
                "sort_order": s.sort_order,
                "content": s.content,
                "source_snapshot": s.source_snapshot,
                "source_metadata": s.source_metadata,
                "is_custom": s.is_custom,
            }
            for s in report.sections
        ],
        "evidences": [
            {
                "evidence_id": str(e.evidence_id),
                "section_key": next(
                    (s.section_key for s in report.sections if s.id == e.section_id), None
                ),
                "sort_order": e.sort_order,
                "caption": e.caption,
                "is_enabled": e.is_enabled,
            }
            for e in report.evidences
        ],
    }


def create(
    db: Session, report: Report, user: User, version: int, note: str | None
) -> ReportRevision:
    _assert_editable(report, version)
    number = (
        db.scalar(
            select(func.max(ReportRevision.revision_number)).where(
                ReportRevision.report_id == report.id
            )
        )
        or 0
    ) + 1
    revision = ReportRevision(
        report_id=report.id,
        revision_number=number,
        snapshot=snapshot(report),
        created_by=user.id,
        note=note,
    )
    db.add(revision)
    report.edit_version += 1
    db.commit()
    db.refresh(revision)
    return revision


def list_all(db: Session, report: Report):
    return list(
        db.scalars(
            select(ReportRevision)
            .where(ReportRevision.report_id == report.id)
            .order_by(ReportRevision.revision_number.desc())
        ).all()
    )


def restore(db: Session, report: Report, revision_id: UUID, version: int):
    _assert_editable(report, version)
    revision = db.scalar(
        select(ReportRevision).where(
            ReportRevision.id == revision_id, ReportRevision.report_id == report.id
        )
    )
    if not revision:
        raise HTTPException(404, "Revision not found")
    data = revision.snapshot
    report.title = data["title"]
    report.summary = data.get("summary")
    report.template_key = data.get("template_key", "ENVIRONMENTAL_PREMIUM")
    report.theme = data.get("theme", {})
    report.editorial_config = data.get("editorial_config", {})
    report.composition_mode = ReportCompositionMode(data.get("composition_mode", "AUTO"))
    db.query(ReportPage).filter(ReportPage.report_id == report.id).delete(synchronize_session=False)
    db.query(ReportLayoutOverride).filter(ReportLayoutOverride.report_id == report.id).delete(
        synchronize_session=False
    )
    db.query(ReportEvidence).filter(ReportEvidence.report_id == report.id).delete(
        synchronize_session=False
    )
    db.query(ReportSection).filter(ReportSection.report_id == report.id).delete(
        synchronize_session=False
    )
    db.flush()
    by_key = {}
    for raw in data["sections"]:
        section = ReportSection(report_id=report.id, **raw)
        db.add(section)
        db.flush()
        by_key[section.section_key] = section
    for raw in data["evidences"]:
        raw = dict(raw)
        section_key = raw.pop("section_key", None)
        db.add(
            ReportEvidence(
                report_id=report.id,
                section_id=by_key[section_key].id if section_key else None,
                **raw,
            )
        )
    for raw_page in data.get("pages", []):
        raw_page = dict(raw_page)
        raw_page.pop("id", None)
        elements = raw_page.pop("elements", [])
        page = ReportPage(report_id=report.id, **raw_page)
        db.add(page)
        db.flush()
        for raw_element in elements:
            raw_element = dict(raw_element)
            raw_element.pop("id", None)
            raw_element["metadata_"] = raw_element.pop("metadata", {})
            db.add(ReportElement(page_id=page.id, **raw_element))
    for raw_override in data.get("layout_overrides", []):
        db.add(ReportLayoutOverride(report_id=report.id, **raw_override))
    report.edit_version += 1
    db.commit()
