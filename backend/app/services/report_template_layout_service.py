from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.core import ReportElement, ReportPage, ReportTemplateLayout, User
from app.models.enums import ReportCompositionMode
from app.schemas.report_schema import ReportTemplateLayoutCreate
from app.services.report_service import _ensure_admin, ensure_can_access_report


def _snapshot_pages(report) -> list[dict]:
    return [
        {
            "page_number": page.page_number,
            "name": page.name,
            "width": page.width,
            "height": page.height,
            "background": page.background,
            "background_image": None,
            "is_enabled": page.is_enabled,
            "elements": [
                {
                    "type": element.type.value,
                    "x": element.x,
                    "y": element.y,
                    "width": element.width,
                    "height": element.height,
                    "rotation": element.rotation,
                    "z_index": element.z_index,
                    "locked": element.locked,
                    "visible": element.visible,
                    "content": (
                        {
                            key: value
                            for key, value in (element.content or {}).items()
                            if key not in {"uri", "evidence_id"}
                        }
                        if element.type.value == "IMAGE"
                        else element.content
                    ),
                    "style": element.style,
                    "data_binding": element.data_binding,
                    "metadata": element.metadata_,
                }
                for element in page.elements
            ],
        }
        for page in report.pages
    ]


def list_templates(db: Session, user: User) -> list[ReportTemplateLayout]:
    _ensure_admin(user)
    return list(
        db.scalars(
            select(ReportTemplateLayout).order_by(
                ReportTemplateLayout.is_system.desc(), ReportTemplateLayout.name
            )
        )
    )


def save(
    db: Session, report_id: UUID, payload: ReportTemplateLayoutCreate, user: User
) -> ReportTemplateLayout:
    _ensure_admin(user)
    report = ensure_can_access_report(db, user, report_id)
    if not report.pages:
        raise HTTPException(409, "The report has no freeform pages")
    template = ReportTemplateLayout(
        name=payload.name,
        description=payload.description,
        pages=_snapshot_pages(report),
        created_by=user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def apply(db: Session, report_id: UUID, template_id: UUID, user: User) -> list[ReportPage]:
    _ensure_admin(user)
    report = ensure_can_access_report(db, user, report_id)
    template = db.get(ReportTemplateLayout, template_id)
    if not template:
        raise HTTPException(404, "Report layout template not found")
    db.execute(delete(ReportPage).where(ReportPage.report_id == report.id))
    db.flush()
    result = []
    for raw in deepcopy(template.pages):
        elements = raw.pop("elements", [])
        page = ReportPage(report_id=report.id, **raw)
        db.add(page)
        db.flush()
        for element_raw in elements:
            element_raw["metadata_"] = element_raw.pop("metadata", {})
            db.add(ReportElement(page_id=page.id, **element_raw))
        result.append(page)
    report.composition_mode = ReportCompositionMode.FREEFORM
    db.commit()
    return result
