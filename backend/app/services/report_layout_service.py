from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import Report, ReportElement, ReportPage, User
from app.models.enums import ReportCompositionMode
from app.schemas.report_schema import (
    ReportElementBatchUpdate,
    ReportElementCreate,
    ReportElementUpdate,
    ReportPageCreate,
    ReportPageUpdate,
)
from app.services.report_service import _ensure_admin, ensure_can_access_report
from app.services.report_data_binding_registry import canonical_key


def _editable_report(db: Session, report_id: UUID, user: User) -> Report:
    _ensure_admin(user)
    return ensure_can_access_report(db, user, report_id)


def _page(db: Session, report_id: UUID, page_id: UUID) -> ReportPage:
    page = db.scalar(
        select(ReportPage).where(ReportPage.id == page_id, ReportPage.report_id == report_id)
    )
    if not page:
        raise HTTPException(404, "Report page not found")
    return page


def _element(db: Session, report_id: UUID, element_id: UUID) -> ReportElement:
    element = db.scalar(
        select(ReportElement)
        .join(ReportPage)
        .where(ReportElement.id == element_id, ReportPage.report_id == report_id)
    )
    if not element:
        raise HTTPException(404, "Report element not found")
    return element


def _validate_bounds(page: ReportPage, values: dict, current: ReportElement | None = None) -> None:
    resolved = {
        key: values.get(key, getattr(current, key, None)) for key in ("x", "y", "width", "height")
    }
    if (
        resolved["x"] + resolved["width"] > page.width
        or resolved["y"] + resolved["height"] > page.height
    ):
        raise HTTPException(422, "Element must remain inside the page")


def _validate_binding(values: dict) -> None:
    if "data_binding" not in values or values["data_binding"] is None:
        return
    try:
        canonical_key(values["data_binding"])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _validate_content(
    db: Session, report: Report, values: dict, current: ReportElement | None = None
) -> None:
    element_type = values.get("type", current.type if current else None)
    content = values.get("content", current.content if current else {}) or {}
    if getattr(element_type, "value", element_type) == "IMAGE" and content.get("evidence_id"):
        from app.services.report_visual_data_service import validate_evidence

        validate_evidence(db, report, UUID(str(content["evidence_id"])))
    if getattr(element_type, "value", element_type) == "CHART":
        from app.services.report_visual_data_service import CHART_TYPES

        if content.get("chart_type", "BAR") not in CHART_TYPES:
            raise HTTPException(422, "Unsupported chart type")


def list_pages(db: Session, report_id: UUID, user: User) -> list[ReportPage]:
    _editable_report(db, report_id, user)
    return list(
        db.scalars(
            select(ReportPage)
            .options(selectinload(ReportPage.elements))
            .where(ReportPage.report_id == report_id)
            .order_by(ReportPage.page_number)
        ).unique()
    )


def create_page(db: Session, report_id: UUID, payload: ReportPageCreate, user: User) -> ReportPage:
    report = _editable_report(db, report_id, user)
    number = (
        db.scalar(select(func.max(ReportPage.page_number)).where(ReportPage.report_id == report_id))
        or 0
    ) + 1
    page = ReportPage(report_id=report_id, page_number=number, **payload.model_dump())
    db.add(page)
    report.composition_mode = ReportCompositionMode.FREEFORM
    db.commit()
    db.refresh(page)
    return page


def update_page(
    db: Session, report_id: UUID, page_id: UUID, payload: ReportPageUpdate, user: User
) -> ReportPage:
    _editable_report(db, report_id, user)
    page = _page(db, report_id, page_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(page, key, value)
    for element in page.elements:
        _validate_bounds(page, {}, element)
    db.commit()
    db.refresh(page)
    return page


def delete_page(db: Session, report_id: UUID, page_id: UUID, user: User) -> None:
    _editable_report(db, report_id, user)
    page = _page(db, report_id, page_id)
    deleted_number = page.page_number
    db.delete(page)
    db.flush()
    for item in db.scalars(
        select(ReportPage)
        .where(ReportPage.report_id == report_id, ReportPage.page_number > deleted_number)
        .order_by(ReportPage.page_number)
    ):
        item.page_number -= 1
    remaining = (
        db.scalar(
            select(func.count()).select_from(ReportPage).where(ReportPage.report_id == report_id)
        )
        or 0
    )
    if not remaining:
        report = db.get(Report, report_id)
        report.composition_mode = ReportCompositionMode.AUTO
    db.commit()


def create_element(
    db: Session, report_id: UUID, page_id: UUID, payload: ReportElementCreate, user: User
) -> ReportElement:
    report = _editable_report(db, report_id, user)
    page = _page(db, report_id, page_id)
    values = payload.model_dump()
    _validate_bounds(page, values)
    _validate_binding(values)
    _validate_content(db, report, values)
    values["metadata_"] = values.pop("metadata")
    element = ReportElement(page_id=page.id, **values)
    db.add(element)
    db.commit()
    db.refresh(element)
    return element


def update_element(
    db: Session, report_id: UUID, element_id: UUID, payload: ReportElementUpdate, user: User
) -> ReportElement:
    report = _editable_report(db, report_id, user)
    element = _element(db, report_id, element_id)
    values = payload.model_dump(exclude_unset=True)
    _validate_bounds(element.page, values, element)
    _validate_binding(values)
    _validate_content(db, report, values, element)
    if "metadata" in values:
        values["metadata_"] = values.pop("metadata")
    for key, value in values.items():
        setattr(element, key, value)
    db.commit()
    db.refresh(element)
    return element


def delete_element(db: Session, report_id: UUID, element_id: UUID, user: User) -> None:
    _editable_report(db, report_id, user)
    db.delete(_element(db, report_id, element_id))
    db.commit()


def batch_update(
    db: Session, report_id: UUID, page_id: UUID, payload: ReportElementBatchUpdate, user: User
) -> list[ReportElement]:
    report = _editable_report(db, report_id, user)
    page = _page(db, report_id, page_id)
    ids = [item.id for item in payload.elements]
    elements = list(
        db.scalars(
            select(ReportElement).where(ReportElement.page_id == page.id, ReportElement.id.in_(ids))
        )
    )
    if len(elements) != len(set(ids)):
        raise HTTPException(404, "One or more report elements were not found")
    lookup = {item.id: item for item in elements}
    for change in payload.elements:
        element = lookup[change.id]
        values = change.model_dump(exclude={"id"}, exclude_unset=True)
        _validate_bounds(page, values, element)
        _validate_binding(values)
        _validate_content(db, report, values, element)
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        for key, value in values.items():
            setattr(element, key, value)
    db.commit()
    return sorted(elements, key=lambda item: item.z_index)
