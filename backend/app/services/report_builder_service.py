from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import (
    Evidence,
    Event,
    EventSession,
    Report,
    ReportEvidence,
    ReportSection,
    User,
)
from app.models.enums import (
    ReportLayoutVariant,
    ReportScope,
    ReportSectionType,
    ReportStatus,
    ReportTemplateKey,
    UserRole,
)
from app.schemas.report_schema import (
    CustomSectionCreate,
    EvidenceAdd,
    EvidenceUpdate,
    ReportUpdate,
    SectionOrderUpdate,
    SectionUpdate,
)
from app.services import report_autofill_service
from app.services.report_service import _ensure_admin, _ensure_can_access_event

TITLES = {
    "cover": "Portada",
    "executive_summary": "Resumen ejecutivo",
    "event_info": "Datos del evento",
    "show_info": "Datos del show",
    "services": "Servicios",
    "operations": "Operación",
    "staff": "Personal",
    "tasks": "Tareas",
    "incidents": "Incidencias",
    "forms": "Formularios",
    "bike_zone": "Bike Zone",
    "waste": "Residuos",
    "carbon": "Huella de carbono",
    "environmental_impact": "Impacto ambiental evitado",
    "evidences": "Evidencias",
    "recommendations": "Recomendaciones",
    "conclusion": "Conclusión",
}
EVENT_ORDER = [
    "cover",
    "executive_summary",
    "event_info",
    "services",
    "operations",
    "staff",
    "tasks",
    "incidents",
    "forms",
    "bike_zone",
    "waste",
    "carbon",
    "environmental_impact",
    "evidences",
    "recommendations",
    "conclusion",
]
SHOW_ORDER = [
    "cover",
    "executive_summary",
    "event_info",
    "show_info",
    "staff",
    "tasks",
    "incidents",
    "forms",
    "bike_zone",
    "evidences",
    "conclusion",
    "services",
    "waste",
    "carbon",
    "environmental_impact",
]
DEFAULT_LAYOUTS = {
    "cover": ReportLayoutVariant.HERO_IMAGE_TEXT,
    "executive_summary": ReportLayoutVariant.EDITORIAL,
    "event_info": ReportLayoutVariant.TWO_COLUMN,
    "show_info": ReportLayoutVariant.TWO_COLUMN,
    "services": ReportLayoutVariant.METRIC_LIST,
    "operations": ReportLayoutVariant.EDITORIAL,
    "staff": ReportLayoutVariant.KPI_GRID,
    "tasks": ReportLayoutVariant.BIG_NUMBERS,
    "incidents": ReportLayoutVariant.METRIC_LIST,
    "forms": ReportLayoutVariant.FEATURE_CHART,
    "bike_zone": ReportLayoutVariant.BIG_NUMBERS,
    "waste": ReportLayoutVariant.FEATURE_CHART,
    "carbon": ReportLayoutVariant.FEATURE_CHART,
    "environmental_impact": ReportLayoutVariant.FEATURE_CHART,
    "evidences": ReportLayoutVariant.PHOTO_GRID,
    "recommendations": ReportLayoutVariant.TEXT_IMAGE,
    "conclusion": ReportLayoutVariant.EDITORIAL,
}

ENVIRONMENTAL_STORY_ORDER = [
    "cover",
    "executive_summary",
    "event_info",
    "show_info",
    "waste",
    "bike_zone",
    "carbon",
    "environmental_impact",
    "preset_eco_equivalences",
    "evidences",
    "conclusion",
]


def _apply_environmental_story_preset(db: Session, report: Report) -> None:
    sections = list(report.sections)
    lookup = {section.section_key: section for section in sections}
    equivalences = lookup.get("preset_eco_equivalences")
    if not equivalences:
        equivalences = ReportSection(
            report_id=report.id,
            section_key="preset_eco_equivalences",
            section_type=ReportSectionType.CUSTOM,
            title="Ecoequivalencias",
            layout_variant=ReportLayoutVariant.METRIC_LIST,
            is_enabled=True,
            sort_order=len(sections),
            is_custom=True,
            content={
                "text": "Equivalencias ambientales de los resultados obtenidos.",
                "fields": [
                    {
                        "key": "trees",
                        "label": "Árboles equivalentes",
                        "auto_value": None,
                        "value": "Completar",
                        "unit": None,
                        "description": None,
                        "is_overridden": True,
                        "source": "MANUAL",
                        "is_visible": True,
                    },
                    {
                        "key": "avoided_co2",
                        "label": "CO₂ evitado",
                        "auto_value": None,
                        "value": "Completar",
                        "unit": "t CO₂-e",
                        "description": None,
                        "is_overridden": True,
                        "source": "MANUAL",
                        "is_visible": True,
                    },
                    {
                        "key": "diverted_waste",
                        "label": "Residuos desviados",
                        "auto_value": None,
                        "value": "Completar",
                        "unit": "kg",
                        "description": None,
                        "is_overridden": True,
                        "source": "MANUAL",
                        "is_visible": True,
                    },
                    {
                        "key": "saved_water",
                        "label": "Agua ahorrada",
                        "auto_value": None,
                        "value": "Completar",
                        "unit": "m³",
                        "description": None,
                        "is_overridden": True,
                        "source": "MANUAL",
                        "is_visible": True,
                    },
                ],
                "items": [],
            },
            source_snapshot={},
            source_metadata={"availability": "AVAILABLE", "source_scope": "MANUAL"},
        )
        db.add(equivalences)
        sections.append(equivalences)
        lookup[equivalences.section_key] = equivalences

    official_section = lookup.get("environmental_impact")
    official = (
        (official_section.source_snapshot or {}).get("official_data") or {}
        if official_section
        else {}
    )
    equivalence_fields = [
        {
            "key": f"equivalence_{index}",
            "label": item["name"],
            "auto_value": item["value"],
            "value": item["value"],
            "unit": item["unit"],
            "description": f"{item['source']} · {item['year']}",
            "is_overridden": False,
            "source": "APPROVED_ENVIRONMENTAL_ACTIONS",
            "is_visible": True,
        }
        for index, item in enumerate(official.get("equivalences") or [])
    ]
    equivalences.content = {
        "text": official.get("disclaimer"),
        "fields": equivalence_fields,
        "items": [],
    }
    equivalences.source_snapshot = equivalences.content
    equivalences.source_metadata = {
        "availability": "AVAILABLE" if equivalence_fields else "NO_DATA",
        "source_scope": "APPROVED_ENVIRONMENTAL_ACTIONS",
    }
    equivalences.is_custom = False

    layouts = {
        "waste": ReportLayoutVariant.METRIC_LIST,
        "bike_zone": ReportLayoutVariant.BIG_NUMBERS,
        "carbon": ReportLayoutVariant.METRIC_LIST,
        "preset_eco_equivalences": ReportLayoutVariant.METRIC_LIST,
        "evidences": ReportLayoutVariant.PHOTO_GRID,
    }
    active = set(ENVIRONMENTAL_STORY_ORDER)
    for section in sections:
        section.is_enabled = section.section_key in active and section.source_metadata.get(
            "availability"
        ) not in {"NO_DATA", "NOT_APPLICABLE"}
        if section.section_key in layouts:
            section.layout_variant = layouts[section.section_key]
    equivalences.is_enabled = bool(equivalence_fields)
    ordered = sorted(
        sections,
        key=lambda section: (
            ENVIRONMENTAL_STORY_ORDER.index(section.section_key)
            if section.section_key in ENVIRONMENTAL_STORY_ORDER
            else len(ENVIRONMENTAL_STORY_ORDER),
            section.sort_order,
        ),
    )
    for position, section in enumerate(ordered):
        section.sort_order = position


def _conflict():
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="El reporte cambió en otra sesión. Recarga el editor antes de guardar.",
    )


def _assert_editable(report: Report, version: int):
    if report.status == ReportStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="No se pueden editar reportes archivados")
    if report.edit_version != version:
        _conflict()


def get_editor(db: Session, report_id: UUID, user: User) -> Report:
    report = db.scalar(
        select(Report)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Report.event).selectinload(Event.client),
            selectinload(Report.session),
            selectinload(Report.sections),
            selectinload(Report.evidences).selectinload(ReportEvidence.evidence),
        )
        .where(Report.id == report_id, Report.status != ReportStatus.ARCHIVED)
    )
    if not report:
        raise HTTPException(404, "Report not found")
    _ensure_can_access_event(db, user, report.event_id)
    if report.status == ReportStatus.DRAFT and user.role not in {
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    }:
        raise HTTPException(404, "Report not found")
    report.sections.sort(key=lambda item: item.sort_order)
    report.evidences.sort(key=lambda item: item.sort_order)
    return report


def create_draft(
    db: Session, event_id: UUID, scope: ReportScope, session_id: UUID | None, user: User
) -> Report:
    _ensure_admin(user)
    event = _ensure_can_access_event(db, user, event_id)
    session = None
    if scope == ReportScope.SHOW:
        session = db.scalar(
            select(EventSession).where(
                EventSession.id == session_id, EventSession.event_id == event_id
            )
        )
        if not session:
            raise HTTPException(409, "El show no pertenece al evento")
    report = Report(
        event_id=event_id,
        scope=scope,
        session_id=session_id,
        title=f"Reporte {'del show ' + session.name if session else 'del evento ' + event.name}",
        status=ReportStatus.DRAFT,
        created_by=user.id,
    )
    db.add(report)
    db.flush()
    generated = report_autofill_service.build_sections(db, event, session)
    order = SHOW_ORDER if session else EVENT_ORDER
    for position, key in enumerate(order):
        content, snapshot, metadata = generated[key]
        enabled = metadata["availability"] not in {"NO_DATA", "NOT_APPLICABLE"}
        db.add(
            ReportSection(
                report_id=report.id,
                section_key=key,
                section_type=ReportSectionType(key.upper()),
                title=TITLES[key],
                layout_variant=DEFAULT_LAYOUTS[key],
                is_enabled=enabled,
                sort_order=position,
                content=content,
                source_snapshot=snapshot,
                source_metadata=metadata,
            )
        )
    db.commit()
    return get_editor(db, report.id, user)


def update_report(db: Session, report: Report, payload: ReportUpdate) -> Report:
    _assert_editable(report, payload.edit_version)
    for field in ("title", "summary"):
        value = getattr(payload, field)
        if value is not None:
            setattr(report, field, value)
    if payload.template_key is not None:
        if (
            payload.template_key == ReportTemplateKey.ENVIRONMENTAL_STORY
            and report.template_key != payload.template_key
        ):
            _apply_environmental_story_preset(db, report)
        report.template_key = payload.template_key
    if payload.theme is not None:
        report.theme = payload.theme.model_dump()
    if payload.editorial_config is not None:
        report.editorial_config = payload.editorial_config.model_dump(mode="json")
    report.edit_version += 1
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    return report


def update_section(
    db: Session, report: Report, section_id: UUID, payload: SectionUpdate
) -> ReportSection:
    _assert_editable(report, payload.edit_version)
    section = db.scalar(
        select(ReportSection).where(
            ReportSection.id == section_id, ReportSection.report_id == report.id
        )
    )
    if not section:
        raise HTTPException(404, "Section not found")
    if payload.title is not None:
        section.title = payload.title
    if payload.is_enabled is not None:
        section.is_enabled = payload.is_enabled
    if payload.layout_variant is not None:
        section.layout_variant = payload.layout_variant
    if payload.content is not None:
        content = payload.content.model_dump(mode="json")
        automatic = {f["key"]: f for f in section.source_snapshot.get("fields", [])}
        for field in content.get("fields", []):
            auto = automatic.get(field["key"])
            if auto:
                field["auto_value"] = auto.get("auto_value")
                field["is_overridden"] = field.get("value") != auto.get("auto_value")
        section.content = content
    section.edit_version += 1
    section.updated_at = datetime.utcnow()
    report.edit_version += 1
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(section)
    return section


def add_custom_section(db: Session, report: Report, payload: CustomSectionCreate) -> ReportSection:
    _assert_editable(report, payload.edit_version)
    order = (
        db.scalar(
            select(func.coalesce(func.max(ReportSection.sort_order), -1)).where(
                ReportSection.report_id == report.id
            )
        )
        + 1
    )
    key = f"custom_{uuid4().hex[:12]}"
    raw = payload.content.model_dump(mode="json")
    fields = []
    if raw["kind"] == "INDICATOR":
        fields = [
            {
                "key": "manual_indicator",
                "label": raw["label"],
                "auto_value": None,
                "value": raw["value"],
                "unit": raw.get("unit"),
                "description": raw.get("description"),
                "is_overridden": True,
                "source": "MANUAL",
            }
        ]
    section = ReportSection(
        report_id=report.id,
        section_key=key,
        section_type=ReportSectionType.CUSTOM,
        title=payload.title,
        layout_variant=ReportLayoutVariant.EDITORIAL,
        is_enabled=True,
        sort_order=order,
        is_custom=True,
        content={"text": raw.get("text"), "fields": fields, "items": []},
        source_snapshot={},
        source_metadata={"availability": "AVAILABLE", "source_scope": "MANUAL"},
    )
    db.add(section)
    report.edit_version += 1
    db.commit()
    db.refresh(section)
    return section


def reorder(db: Session, report: Report, payload: SectionOrderUpdate) -> None:
    _assert_editable(report, payload.edit_version)
    sections = list(
        db.scalars(select(ReportSection).where(ReportSection.report_id == report.id)).all()
    )
    if len(payload.section_ids) != len(set(payload.section_ids)) or set(payload.section_ids) != {
        s.id for s in sections
    }:
        raise HTTPException(
            400, "section_ids debe contener todas las secciones exactamente una vez"
        )
    lookup = {s.id: s for s in sections}
    for order, section_id in enumerate(payload.section_ids):
        lookup[section_id].sort_order = order
    report.edit_version += 1
    db.commit()


def remove_custom_section(db: Session, report: Report, section_id: UUID, version: int) -> None:
    _assert_editable(report, version)
    section = next((item for item in report.sections if item.id == section_id), None)
    if not section:
        raise HTTPException(404, "Section not found")
    if not section.is_custom:
        raise HTTPException(409, "Las secciones automáticas solo se pueden ocultar")

    for evidence in section.evidences:
        evidence.section_id = None
    db.delete(section)
    remaining = sorted(
        (item for item in report.sections if item.id != section_id),
        key=lambda item: item.sort_order,
    )
    for order, item in enumerate(remaining):
        item.sort_order = order

    config = dict(report.editorial_config or {})
    overrides = dict(config.get("page_overrides") or {})
    overrides.pop(section.section_key, None)
    for key, override in list(overrides.items()):
        if override.get("group_with") == section.section_key:
            overrides[key] = {"mode": "AUTO"}
    config["page_overrides"] = overrides
    report.editorial_config = config
    report.edit_version += 1
    report.updated_at = datetime.utcnow()
    db.commit()


def refresh(db: Session, report: Report, version: int, user: User) -> Report:
    _assert_editable(report, version)
    event = _ensure_can_access_event(db, user, report.event_id)
    session = db.get(EventSession, report.session_id) if report.session_id else None
    fresh = report_autofill_service.build_sections(db, event, session)
    for section in report.sections:
        if section.is_custom or section.section_key not in fresh:
            continue
        content, snapshot, metadata = fresh[section.section_key]
        section.content = report_autofill_service.merge_preserving_overrides(
            section.content, content
        )
        section.source_snapshot = snapshot
        section.source_metadata = metadata
        section.edit_version += 1
        section.updated_at = datetime.utcnow()
    report.edit_version += 1
    report.updated_at = datetime.utcnow()
    db.commit()
    return get_editor(db, report.id, user)


def reset_field(
    db: Session, report: Report, section_id: UUID, field_key: str, version: int, user: User
) -> ReportSection:
    _assert_editable(report, version)
    section = next((s for s in report.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(404, "Section not found")
    auto = next(
        (f for f in section.source_snapshot.get("fields", []) if f.get("key") == field_key), None
    )
    if not auto:
        raise HTTPException(404, "Automatic field not found")
    content = dict(section.content)
    fields = [dict(f) for f in content.get("fields", [])]
    current = next((f for f in fields if f.get("key") == field_key), None)
    if not current:
        raise HTTPException(404, "Field not found")
    current.update(
        value=auto.get("auto_value"), auto_value=auto.get("auto_value"), is_overridden=False
    )
    content["fields"] = fields
    section.content = content
    section.edit_version += 1
    report.edit_version += 1
    db.commit()
    db.refresh(section)
    return section


def available_evidences(db: Session, report: Report):
    query = select(Evidence).where(Evidence.event_id == report.event_id)
    if report.scope == ReportScope.SHOW:
        query = query.where(Evidence.session_id == report.session_id)
    selected = {item.evidence_id for item in report.evidences}
    return [
        {
            "id": e.id,
            "file_type": e.file_type,
            "description": e.description,
            "taken_at": e.taken_at,
            "session_id": e.session_id,
            "preview_url": f"/api/v1/evidences/{e.id}/download",
            "selected": e.id in selected,
        }
        for e in db.scalars(query.order_by(Evidence.created_at.desc())).all()
    ]


def add_evidence(db: Session, report: Report, payload: EvidenceAdd) -> ReportEvidence:
    _assert_editable(report, payload.edit_version)
    evidence = db.get(Evidence, payload.evidence_id)
    if (
        not evidence
        or evidence.event_id != report.event_id
        or (report.scope == ReportScope.SHOW and evidence.session_id != report.session_id)
    ):
        raise HTTPException(409, "La evidencia no pertenece al alcance del reporte")
    if payload.section_id and not db.scalar(
        select(ReportSection.id).where(
            ReportSection.id == payload.section_id, ReportSection.report_id == report.id
        )
    ):
        raise HTTPException(404, "Section not found")
    order = (
        db.scalar(
            select(func.count())
            .select_from(ReportEvidence)
            .where(ReportEvidence.report_id == report.id)
        )
        or 0
    )
    item = ReportEvidence(
        report_id=report.id,
        evidence_id=evidence.id,
        section_id=payload.section_id,
        caption=payload.caption,
        sort_order=order,
    )
    db.add(item)
    report.edit_version += 1
    db.commit()
    db.refresh(item)
    return item


def remove_evidence(db: Session, report: Report, item_id: UUID, version: int):
    _assert_editable(report, version)
    item = db.scalar(
        select(ReportEvidence).where(
            ReportEvidence.id == item_id, ReportEvidence.report_id == report.id
        )
    )
    if not item:
        raise HTTPException(404, "Report evidence not found")
    db.delete(item)
    report.edit_version += 1
    db.commit()


def update_evidence(
    db: Session, report: Report, item_id: UUID, payload: EvidenceUpdate
) -> ReportEvidence:
    _assert_editable(report, payload.edit_version)
    item = db.scalar(
        select(ReportEvidence).where(
            ReportEvidence.id == item_id, ReportEvidence.report_id == report.id
        )
    )
    if not item:
        raise HTTPException(404, "Report evidence not found")
    if payload.section_id and not db.scalar(
        select(ReportSection.id).where(
            ReportSection.id == payload.section_id,
            ReportSection.report_id == report.id,
        )
    ):
        raise HTTPException(404, "Section not found")
    item.section_id = payload.section_id
    item.caption = payload.caption
    if payload.is_enabled is not None:
        item.is_enabled = payload.is_enabled
    report.edit_version += 1
    db.commit()
    db.refresh(item)
    return item
