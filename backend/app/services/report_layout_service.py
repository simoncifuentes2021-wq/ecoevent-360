from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import Report, ReportElement, ReportPage, User
from app.models.enums import ReportCompositionMode, ReportElementType
from app.schemas.report_schema import (
    ReportElementBatchUpdate,
    ReportElementCreate,
    ReportElementUpdate,
    ReportPageCreate,
    ReportPageUpdate,
)
from app.services.report_service import _ensure_admin, ensure_can_access_report
from app.services.report_data_binding_registry import canonical_key


PAGE_WIDTH = 1000.0
PAGE_HEIGHT = 1414.0
AUTO_LAYOUT_VERSION = 2


def _auto_element(page: ReportPage, kind: ReportElementType, **values) -> ReportElement:
    return ReportElement(
        page_id=page.id,
        type=kind,
        rotation=0,
        locked=False,
        visible=True,
        metadata_={"materialized_from_auto": True, "auto_layout_version": AUTO_LAYOUT_VERSION},
        data_binding=values.pop("data_binding", None),
        content=values.pop("content", {}),
        style=values.pop("style", {}),
        **values,
    )


def _field_binding(section_key: str, field_key: str) -> dict | None:
    from app.services.report_data_binding_registry import REGISTRY

    match = next(
        (
            definition
            for definition in REGISTRY.values()
            if definition.source == section_key and definition.key.rsplit(".", 1)[-1] == field_key
        ),
        None,
    )
    return {"key": match.key} if match else None


def _is_legacy_placeholder_layout(pages: list[ReportPage]) -> bool:
    """Recognize only untouched canvases created by the first experimental editor."""
    if not pages:
        return False
    defaults = {"", "Título de página", "Escribe aquí", "Sin datos"}
    elements = [element for page in pages for element in page.elements]
    return (
        all(page.background == "#FFFFFF" and (page.name or "").startswith("Página") for page in pages)
        and all(
            not element.metadata_
            and not element.data_binding
            and set((element.content or {}).keys()) <= {"text"}
            and str((element.content or {}).get("text") or "") in defaults
            for element in elements
        )
    )


def _is_replaceable_auto_layout(report: Report, pages: list[ReportPage]) -> bool:
    """Upgrade generated canvases, but never overwrite a canvas the user has edited."""
    if (report.editorial_config or {}).get("freeform_user_edited"):
        return False
    elements = [element for page in pages for element in page.elements]
    return bool(elements) and all(
        (element.metadata_ or {}).get("materialized_from_auto")
        and (element.metadata_ or {}).get("auto_layout_version") != AUTO_LAYOUT_VERSION
        for element in elements
    )


def _page_chrome(page: ReportPage, title: str, number: int, theme: dict) -> list[ReportElement]:
    primary = str(theme["primary_color"])
    muted = str(theme["muted_color"])
    background = str(theme["background_color"])
    return [
        _auto_element(page, ReportElementType.SHAPE, x=885, y=0, width=115, height=115, z_index=0, style={"background": background, "borderRadius": 58}),
        _auto_element(page, ReportElementType.TEXT, x=70, y=64, width=620, height=32, z_index=2, content={"text": title.upper()}, style={"fontSize": 10, "fontWeight": "800", "color": primary, "letterSpacing": 2}),
        _auto_element(page, ReportElementType.TEXT, x=790, y=64, width=140, height=32, z_index=2, content={"text": "EcoEvent 360"}, style={"fontSize": 10, "textAlign": "right", "color": muted}),
        _auto_element(page, ReportElementType.SHAPE, x=70, y=104, width=860, height=2, z_index=2, style={"background": "#DCE5E0"}),
        _auto_element(page, ReportElementType.TEXT, x=70, y=1350, width=500, height=28, z_index=2, content={"text": "IMPACTO · OPERACIÓN · EVIDENCIA"}, style={"fontSize": 9, "color": muted, "letterSpacing": 1}),
        _auto_element(page, ReportElementType.TEXT, x=870, y=1350, width=60, height=28, z_index=2, content={"text": f"{number - 1:02d}"}, style={"fontSize": 10, "fontWeight": "800", "textAlign": "right", "color": primary}),
    ]


def _materialize_section(
    db: Session, report: Report, page: ReportPage, section, top: float, height: float, z: int
) -> list[ReportElement]:
    from app.services.report_visual_data_service import chart_dataset

    from app.services.report_render_service import theme_for_template

    theme = theme_for_template(report.template_key.value, report.theme)
    primary = str(theme["primary_color"])
    accent = str(theme["accent_color"])
    surface = str(theme["background_color"])
    content = section.content or {}
    elements = [
        _auto_element(
            page,
            ReportElementType.SHAPE,
            x=50,
            y=top,
            width=900,
            height=height,
            z_index=z,
            style={"background": surface, "borderRadius": 10, "opacity": 1},
        ),
        _auto_element(
            page,
            ReportElementType.TITLE,
            x=82,
            y=top + 24,
            width=850,
            height=64,
            z_index=z + 1,
            content={"text": section.title},
            style={"fontSize": 30, "fontWeight": "800", "color": primary, "lineHeight": 1.05},
        ),
    ]
    cursor = top + 96
    text_value = content.get("text")
    if text_value:
        elements.append(
            _auto_element(
                page,
                ReportElementType.TEXT,
                x=82,
                y=cursor,
                width=850,
                height=min(120, max(70, height * 0.2)),
                z_index=z + 1,
                content={"text": str(text_value)},
                style={"fontSize": 16, "color": str(theme["muted_color"]), "lineHeight": 1.5},
            )
        )
        cursor += min(135, max(85, height * 0.22))
    fields = [item for item in (content.get("fields") or []) if item.get("is_visible", True)][:4]
    if fields:
        card_width = (850 - (len(fields) - 1) * 14) / len(fields)
        for index, field in enumerate(fields):
            value = field.get("value")
            display = "Sin datos" if value is None else str(value)
            if field.get("unit") and value is not None:
                display += f" {field['unit']}"
            elements.append(
                _auto_element(
                    page,
                    ReportElementType.KPI,
                    x=82 + index * (card_width + 14),
                    y=cursor,
                    width=card_width,
                    height=min(125, max(90, height - (cursor - top) - 24)),
                    z_index=z + 1,
                    content={"text": display, "label": field.get("label")},
                    data_binding=_field_binding(section.section_key, str(field.get("key") or "")),
                    style={"fontSize": 22, "fontWeight": "800", "color": primary, "background": "#FFFFFF", "borderRadius": 10, "padding": 16},
                )
            )
        cursor += min(140, max(105, height - (cursor - top) - 24))
    dataset = chart_dataset(report, section.section_key, "BAR")
    if dataset.get("availability") == "AVAILABLE" and height - (cursor - top) >= 150:
        elements.append(
            _auto_element(
                page,
                ReportElementType.CHART,
                x=75,
                y=cursor,
                width=520,
                height=height - (cursor - top) - 24,
                z_index=z + 1,
                content={"source": section.section_key, "chart_type": "BAR", "dataset": dataset},
                style={"color": accent, "background": "#FFFFFF", "borderRadius": 12},
            )
        )
    evidence = next(
        (item for item in report.evidences if item.is_enabled and item.section_id == section.id),
        None,
    )
    if evidence and height - (cursor - top) >= 150:
        elements.append(
            _auto_element(
                page,
                ReportElementType.IMAGE,
                x=615,
                y=cursor,
                width=310,
                height=height - (cursor - top) - 24,
                z_index=z + 2,
                content={"evidence_id": str(evidence.evidence_id), "caption": evidence.caption or evidence.evidence.description},
                style={"objectFit": "cover", "borderRadius": 12},
            )
        )
    return elements


def materialize_auto_layout(
    db: Session, report_id: UUID, user: User, *, force_upgrade: bool = False
) -> list[ReportPage]:
    """Create an editable object model of the professional editorial layout."""
    _ensure_admin(user)
    db.execute(select(Report.id).where(Report.id == report_id).with_for_update())
    report = ensure_can_access_report(db, user, report_id)
    existing = list(
        db.scalars(
            select(ReportPage)
            .options(selectinload(ReportPage.elements))
            .where(ReportPage.report_id == report_id)
            .order_by(ReportPage.page_number)
        ).unique()
    )
    replaceable = (
        force_upgrade
        or _is_legacy_placeholder_layout(existing)
        or _is_replaceable_auto_layout(report, existing)
    )
    if existing and not replaceable:
        return existing
    if existing:
        for page in existing:
            db.delete(page)
        db.flush()

    from app.services.report_page_planner import plan_pages
    from app.services.report_render_service import theme_for_template

    theme = theme_for_template(report.template_key.value, report.theme)
    visible = [section for section in report.sections if section.is_enabled]
    by_key = {section.section_key: section for section in visible}
    plans = plan_pages(
        [
            {
                "section_key": section.section_key,
                "section_type": section.section_type.value,
                "title": section.title,
                "is_enabled": section.is_enabled,
                "sort_order": section.sort_order,
                "content": section.content,
            }
            for section in visible
        ],
        report.template_key.value,
        report.editorial_config,
    )
    pages: list[ReportPage] = []
    for plan in plans:
        page = ReportPage(
            report_id=report.id,
            page_number=plan.number,
            name=plan.title,
            width=PAGE_WIDTH,
            height=PAGE_HEIGHT,
            background="#FFFFFF",
            is_enabled=True,
        )
        db.add(page)
        db.flush()
        pages.append(page)
        if plan.recipe.value == "COVER_HERO":
            primary = str(theme["primary_color"])
            accent = str(theme["accent_color"])
            page.background = primary
            evidence = next((item for item in report.evidences if item.is_enabled), None)
            if evidence:
                page.elements.append(
                    _auto_element(page, ReportElementType.IMAGE, x=0, y=0, width=1000, height=1414, z_index=0, content={"evidence_id": str(evidence.evidence_id), "caption": evidence.caption or evidence.evidence.description}, style={"objectFit": "cover", "borderRadius": 0})
                )
            page.elements.extend(
                [
                    _auto_element(page, ReportElementType.SHAPE, x=0, y=0, width=1000, height=1414, z_index=1, style={"background": primary, "opacity": 0.88}),
                    _auto_element(page, ReportElementType.SHAPE, x=82, y=515, width=118, height=9, z_index=2, style={"background": accent}),
                    _auto_element(page, ReportElementType.TEXT, x=82, y=90, width=720, height=45, z_index=2, content={"text": "ECOEVENT 360 · REPORTE DE IMPACTO"}, style={"fontSize": 12, "fontWeight": "800", "color": "#FFFFFF", "letterSpacing": 3}),
                    _auto_element(page, ReportElementType.TITLE, x=82, y=555, width=820, height=260, z_index=2, content={"text": report.title}, style={"fontSize": 52, "fontWeight": "800", "color": "#FFFFFF", "lineHeight": 0.95}),
                    _auto_element(page, ReportElementType.TEXT, x=82, y=875, width=380, height=105, z_index=2, content={"text": report.event.client.business_name}, data_binding={"key": "event.client"}, style={"fontSize": 22, "fontWeight": "700", "color": "#FFFFFF"}),
                    _auto_element(page, ReportElementType.TEXT, x=82, y=975, width=390, height=95, z_index=2, content={"text": report.event.name}, data_binding={"key": "event.name"}, style={"fontSize": 16, "color": "#D1FAE5"}),
                    _auto_element(page, ReportElementType.TEXT, x=550, y=875, width=365, height=135, z_index=2, content={"text": f"REPORTE INTEGRAL\n{report.event.start_date:%d.%m.%Y} — {report.event.end_date:%d.%m.%Y}"}, style={"fontSize": 16, "fontWeight": "700", "color": "#FFFFFF", "lineHeight": 1.5}),
                ]
            )
            continue
        sections = [by_key[key] for key in plan.section_keys if key in by_key]
        if not sections:
            continue
        page.elements.extend(_page_chrome(page, plan.title, plan.number, theme))
        page.elements.append(_auto_element(page, ReportElementType.TITLE, x=70, y=135, width=840, height=105, z_index=2, content={"text": plan.title}, style={"fontSize": 38, "fontWeight": "800", "color": str(theme["primary_color"]), "lineHeight": 1}))
        block_height = min(1030 / len(sections), 505)
        for index, section in enumerate(sections):
            page.elements.extend(
                _materialize_section(db, report, page, section, 250 + index * (block_height + 18), block_height, 10 + index * 20)
            )
    report.composition_mode = ReportCompositionMode.FREEFORM
    report.edit_version += 1
    db.commit()
    return list_pages(db, report_id, user)


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
