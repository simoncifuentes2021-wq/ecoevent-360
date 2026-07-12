from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import BikeZoneRecord, ClientPortalConfig, ClientPortalSection, ClientPortalWidget, Event, User
from app.models.enums import UserRole
from app.schemas.client_portal_schema import ClientPortalConfigUpdate, ClientPortalSectionUpdate, ClientPortalTemplateApply, ClientPortalWidgetUpdate
from app.services import dashboard_service


SECTION_DEFINITIONS = [
    ("summary", "Resumen", 10),
    ("services", "Servicios", 20),
    ("operation", "Operacion", 30),
    ("incidents", "Incidencias", 40),
    ("evidences", "Evidencias", 50),
    ("waste", "Residuos", 60),
    ("carbon", "Huella", 70),
    ("forms", "Formularios", 80),
    ("bike_zone", "Bike Zone", 90),
    ("reports", "Reportes", 100),
    ("recommendations", "Recomendaciones", 110),
]

WIDGET_DEFINITIONS = [
    ("event_status", "summary", "Estado del evento", 10),
    ("task_completion_rate", "operation", "Cumplimiento de tareas", 20),
    ("open_incidents", "incidents", "Incidencias abiertas", 30),
    ("resolved_incidents", "incidents", "Incidencias resueltas", 40),
    ("evidence_gallery", "evidences", "Galeria de evidencias", 50),
    ("total_waste_kg", "waste", "Residuos totales", 60),
    ("recycling_rate", "waste", "Tasa de recuperacion", 70),
    ("carbon_total_tco2e", "carbon", "Huella total tCO2e", 80),
    ("carbon_per_attendee", "carbon", "Huella por asistente", 90),
    ("forms_total_responses", "forms", "Respuestas de formularios", 100),
    ("forms_transport_modes", "forms", "Modos de transporte", 110),
    ("forms_average_rating", "forms", "Rating promedio", 120),
    ("forms_session_comparison", "forms", "Comparativo por show", 125),
    ("bike_zone_total_registrations", "bike_zone", "Registros Bike Zone", 130),
    ("reports_download", "reports", "Descarga de reportes", 140),
]

TEMPLATES = {
    "ambiental": {"summary", "evidences", "waste", "carbon", "reports", "recommendations"},
    "operativa": {"summary", "services", "operation", "incidents", "evidences", "reports"},
    "experiencia": {"summary", "forms", "recommendations", "reports"},
    "bike_zone": {"summary", "forms", "bike_zone", "reports"},
    "completa_sin_datos_personales": {key for key, _, _ in SECTION_DEFINITIONS},
}


def get_config(db: Session, event_id: UUID, user: User) -> ClientPortalConfig:
    event = _event_or_404(db, event_id)
    _ensure_admin(user)
    return _ensure_config(db, event, user.id)


def update_config(db: Session, event_id: UUID, payload: ClientPortalConfigUpdate, user: User) -> ClientPortalConfig:
    event = _event_or_404(db, event_id)
    _ensure_admin(user)
    config = _ensure_config(db, event, user.id)
    config.scope = payload.scope or "EVENT"
    config.is_active = payload.is_active
    for section in list(config.sections):
        db.delete(section)
    for widget in list(config.widgets):
        db.delete(widget)
    db.flush()

    section_payloads = payload.sections or _default_section_payloads()
    widget_payloads = payload.widgets or _default_widget_payloads()
    known_sections = {key: (label, order) for key, label, order in SECTION_DEFINITIONS}
    known_widgets = {key: (section, label, order) for key, section, label, order in WIDGET_DEFINITIONS}
    for item in section_payloads:
        label, order = known_sections.get(item.section_key, (item.label or item.section_key, item.sort_order))
        db.add(ClientPortalSection(config_id=config.id, section_key=item.section_key, label=item.label or label, is_enabled=item.is_enabled, sort_order=item.sort_order or order))
    for item in widget_payloads:
        default_section, label, order = known_widgets.get(item.widget_key, (item.section_key, item.label or item.widget_key, item.sort_order))
        db.add(ClientPortalWidget(config_id=config.id, widget_key=item.widget_key, section_key=item.section_key or default_section, label=item.label or label, is_enabled=item.is_enabled, sort_order=item.sort_order or order, visibility_config=item.visibility_config or {}))
    db.commit()
    db.expire_all()
    return _load_config(db, config.id)


def apply_template(db: Session, event_id: UUID, payload: ClientPortalTemplateApply, user: User) -> ClientPortalConfig:
    enabled_sections = TEMPLATES.get(payload.template_key)
    if enabled_sections is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client portal template")
    update = ClientPortalConfigUpdate(
        sections=[
            {"section_key": key, "label": label, "is_enabled": key in enabled_sections, "sort_order": order}
            for key, label, order in SECTION_DEFINITIONS
        ],
        widgets=[
            {"widget_key": key, "section_key": section, "label": label, "is_enabled": section in enabled_sections, "sort_order": order}
            for key, section, label, order in WIDGET_DEFINITIONS
        ],
    )
    return update_config(db, event_id, update, user)


def preview_portal(db: Session, event_id: UUID, user: User) -> dict:
    event = _event_or_404(db, event_id)
    _ensure_admin(user)
    config = _ensure_config(db, event, user.id)
    return _portal_payload(db, event, config, user)


def client_portal(db: Session, event_id: UUID, user: User) -> dict:
    event = _event_or_404(db, event_id)
    if user.role != UserRole.CLIENT or user.client_id != event.client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    config = _ensure_config(db, event, user.id)
    return _portal_payload(db, event, config, user)


def _portal_payload(db: Session, event: Event, config: ClientPortalConfig, user: User) -> dict:
    if not config.is_active:
        return {"event_id": event.id, "client_id": event.client_id, "config_id": config.id, "sections": [], "widgets": [], "data": {}}
    enabled_sections = sorted([section for section in config.sections if section.is_enabled], key=lambda item: item.sort_order)
    section_keys = {section.section_key for section in enabled_sections}
    enabled_widgets = sorted(
        [widget for widget in config.widgets if widget.is_enabled and widget.section_key in section_keys],
        key=lambda item: item.sort_order,
    )
    dashboard = dashboard_service.get_event_dashboard(db, event.id, user)
    values = _widget_values(db, event, dashboard)
    visible_widgets = [
        {
            "widget_key": widget.widget_key,
            "section_key": widget.section_key,
            "label": widget.label,
            "sort_order": widget.sort_order,
            "value": values.get(widget.widget_key),
            "data": _widget_data(widget.widget_key, dashboard),
            "visibility_config": widget.visibility_config or {},
        }
        for widget in enabled_widgets
    ]
    return {
        "event_id": event.id,
        "client_id": event.client_id,
        "config_id": config.id,
        "sections": [{"section_key": section.section_key, "label": section.label, "sort_order": section.sort_order} for section in enabled_sections],
        "widgets": visible_widgets,
        "data": {"event": dashboard["event"]},
    }


def _widget_values(db: Session, event: Event, dashboard: dict) -> dict:
    bike_total = db.scalar(select(func.count(BikeZoneRecord.id)).where(BikeZoneRecord.event_id == event.id)) or 0
    return {
        "event_status": str(event.status.value if hasattr(event.status, "value") else event.status),
        "task_completion_rate": dashboard["tasks"]["completion_rate"],
        "open_incidents": dashboard["incidents"]["open"],
        "resolved_incidents": dashboard["incidents"]["resolved"],
        "evidence_gallery": dashboard["evidences"]["total"],
        "total_waste_kg": dashboard["waste"]["total_kg"],
        "recycling_rate": dashboard["waste"]["recovery_rate"],
        "carbon_total_tco2e": dashboard["carbon"]["total_tco2e"],
        "carbon_per_attendee": dashboard["carbon"]["kgco2e_per_attendee"],
        "forms_total_responses": dashboard.get("forms", {}).get("total_form_responses", 0),
        "forms_transport_modes": None,
        "forms_average_rating": dashboard["survey"]["average_rating"],
        "forms_session_comparison": len(dashboard.get("forms_by_session", [])),
        "bike_zone_total_registrations": bike_total,
        "reports_download": None,
    }


def _widget_data(widget_key: str, dashboard: dict) -> dict | list | None:
    if widget_key == "evidence_gallery":
        return dashboard["evidences"]["recent"]
    if widget_key == "forms_transport_modes":
        return []
    if widget_key == "forms_session_comparison":
        return dashboard.get("forms_by_session", [])
    if widget_key == "reports_download":
        return {}
    return None


def _ensure_config(db: Session, event: Event, created_by: UUID | None) -> ClientPortalConfig:
    config = db.scalar(
        select(ClientPortalConfig)
        .options(selectinload(ClientPortalConfig.sections), selectinload(ClientPortalConfig.widgets))
        .where(ClientPortalConfig.event_id == event.id, ClientPortalConfig.client_id == event.client_id)
    )
    if config:
        if _ensure_config_definitions(db, config):
            return _load_config(db, config.id)
        return config
    config = ClientPortalConfig(client_id=event.client_id, event_id=event.id, created_by=created_by)
    db.add(config)
    db.flush()
    for key, label, order in SECTION_DEFINITIONS:
        db.add(ClientPortalSection(config_id=config.id, section_key=key, label=label, sort_order=order))
    for key, section, label, order in WIDGET_DEFINITIONS:
        db.add(ClientPortalWidget(config_id=config.id, widget_key=key, section_key=section, label=label, sort_order=order, visibility_config={}))
    db.commit()
    return _load_config(db, config.id)


def _ensure_config_definitions(db: Session, config: ClientPortalConfig) -> bool:
    existing_sections = {section.section_key for section in config.sections}
    existing_widgets = {widget.widget_key for widget in config.widgets}
    changed = False
    for key, label, order in SECTION_DEFINITIONS:
        if key not in existing_sections:
            db.add(ClientPortalSection(config_id=config.id, section_key=key, label=label, is_enabled=False, sort_order=order))
            changed = True
    for key, section, label, order in WIDGET_DEFINITIONS:
        if key not in existing_widgets:
            db.add(ClientPortalWidget(config_id=config.id, widget_key=key, section_key=section, label=label, is_enabled=False, sort_order=order, visibility_config={}))
            changed = True
    if changed:
        db.commit()
        db.expire_all()
    return changed


def _load_config(db: Session, config_id: UUID) -> ClientPortalConfig:
    config = db.scalar(
        select(ClientPortalConfig)
        .options(selectinload(ClientPortalConfig.sections), selectinload(ClientPortalConfig.widgets))
        .where(ClientPortalConfig.id == config_id)
    )
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client portal config not found")
    config.sections.sort(key=lambda item: item.sort_order)
    config.widgets.sort(key=lambda item: item.sort_order)
    return config


def _event_or_404(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _ensure_admin(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _default_section_payloads() -> list:
    return [ClientPortalSectionUpdate(section_key=key, label=label, is_enabled=True, sort_order=order) for key, label, order in SECTION_DEFINITIONS]


def _default_widget_payloads() -> list:
    return [ClientPortalWidgetUpdate(widget_key=key, section_key=section, label=label, is_enabled=True, sort_order=order) for key, section, label, order in WIDGET_DEFINITIONS]
