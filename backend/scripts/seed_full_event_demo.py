from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import (  # noqa: E402
    Alert,
    CatalogItem,
    ClientPortalConfig,
    ClientPortalSection,
    ClientPortalWidget,
    Event,
    EventOrder,
    EventOrderItem,
    EventZone,
    User,
    WasteCollectionPoint,
    WasteCollectionRecord,
    WasteType,
)
from app.models.enums import (  # noqa: E402
    LogbookAssignmentMode,
    LogbookAssignmentStatus,
    LogbookEvidencePolicy,
    LogbookInstanceStatus,
    LogbookItemType,
    LogbookOperationalStage,
    LogbookResultStatus,
    LogbookTemplateStatus,
    LogbookVersionStatus,
    OrderItemStageStatus,
    OrderStatus,
    PriorityLevel,
)
from app.models.logbook import (  # noqa: E402
    LogbookAssignment,
    LogbookInstance,
    LogbookInstanceItem,
    LogbookItem,
    LogbookResponse,
    LogbookSection,
    LogbookTemplate,
    LogbookTemplateVersion,
)
from app.services.client_portal_service import SECTION_DEFINITIONS, WIDGET_DEFINITIONS  # noqa: E402


def assert_local_database() -> None:
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg://", "postgresql://"))
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("BLOQUEADO: este fixture solo funciona contra PostgreSQL local.")
    if settings.app_env.lower() == "production":
        raise SystemExit("BLOQUEADO: APP_ENV=production.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Completa un evento demo con todos los módulos e indicadores.")
    parser.add_argument("--event-id", help="Evento demo que se desea completar.")
    parser.add_argument("--admin-email", default="admin@ecoevent.cl")
    parser.add_argument("--yes", action="store_true", help="Confirma la escritura en la base local.")
    args = parser.parse_args()
    if not args.yes:
        print("No se modificó nada. Ejecuta con --yes para confirmar.")
        return 2
    assert_local_database()

    with SessionLocal() as db:
        event = _find_event(db, args.event_id)
        admin = db.scalar(select(User).where(User.email == args.admin_email))
        if not admin:
            raise SystemExit(f"No existe el usuario administrador {args.admin_email}.")
        zones = list(db.scalars(select(EventZone).where(EventZone.event_id == event.id).order_by(EventZone.created_at)).all())
        if not zones:
            raise SystemExit("El evento no tiene zonas; ejecuta primero seed_report_engine_demo.py.")
        worker = db.scalar(select(User).where(User.id != admin.id).order_by(User.created_at.asc())) or admin

        _complete_portal_config(db, event, admin)
        _create_collection_data(db, event, zones)
        _create_order_data(db, event, zones, admin, worker)
        _create_alert_data(db, event, zones)
        _create_logbook_data(db, event, zones[0], admin, worker)
        db.commit()

        print("Evento demo integral completado.")
        print(f"event_id: {event.id}")
        print(f"event_name: {event.name}")
        print("Portal cliente: todas las secciones y widgets habilitados.")
        print("Incluye: acopios, pedidos, alertas y bitácoras además de los datos demo existentes.")
    return 0


def _find_event(db, event_id: str | None) -> Event:
    if event_id:
        event = db.get(Event, UUID(event_id))
    else:
        event = db.scalar(select(Event).where(Event.name.startswith("[DEMO COMPARATIVO]")).order_by(Event.created_at.desc()))
    if not event:
        raise SystemExit("No se encontró el evento demo. Ejecuta primero seed_report_engine_demo.py --yes.")
    return event


def _complete_portal_config(db, event: Event, admin: User) -> None:
    config = db.scalar(select(ClientPortalConfig).where(ClientPortalConfig.event_id == event.id, ClientPortalConfig.client_id == event.client_id))
    if not config:
        config = ClientPortalConfig(client_id=event.client_id, event_id=event.id, scope="EVENT", is_active=True, created_by=admin.id)
        db.add(config)
        db.flush()
    config.is_active = True
    sections = {item.section_key: item for item in config.sections}
    widgets = {item.widget_key: item for item in config.widgets}
    for key, label, order in SECTION_DEFINITIONS:
        item = sections.get(key)
        if item:
            item.is_enabled = True
            item.sort_order = order
        else:
            db.add(ClientPortalSection(config_id=config.id, section_key=key, label=label, is_enabled=True, sort_order=order))
    for key, section, label, order in WIDGET_DEFINITIONS:
        item = widgets.get(key)
        if item:
            item.is_enabled = True
            item.section_key = section
            item.sort_order = order
        else:
            db.add(ClientPortalWidget(config_id=config.id, widget_key=key, section_key=section, label=label, is_enabled=True, sort_order=order, visibility_config={}))


def _create_collection_data(db, event: Event, zones: list[EventZone]) -> None:
    points = list(db.scalars(select(WasteCollectionPoint).where(WasteCollectionPoint.event_id == event.id)).all())
    if not points:
        points = [
            WasteCollectionPoint(event_id=event.id, zone_id=zones[0].id, code="DEMO-ACOPIO-01", name="Acopio principal", description="Punto de acopio demo", location_description="Acceso norte", capacity_kg=Decimal("250"), qr_token=f"demo-{uuid4().hex}"),
            WasteCollectionPoint(event_id=event.id, zone_id=zones[-1].id, code="DEMO-ACOPIO-02", name="Acopio backstage", description="Punto de acopio logístico", location_description="Zona de carga", capacity_kg=Decimal("180"), qr_token=f"demo-{uuid4().hex}"),
        ]
        db.add_all(points)
        db.flush()
    waste_type = db.scalar(select(WasteType).where(WasteType.name == "Botellas de plástico PET"))
    if not waste_type:
        waste_type = db.scalar(select(WasteType).where(WasteType.name.ilike("%PET%")))
    if not waste_type:
        waste_type = WasteType(name="Botellas PET demo", is_recyclable=True)
        db.add(waste_type)
        db.flush()
    existing = db.scalar(select(WasteCollectionRecord.id).where(WasteCollectionRecord.event_id == event.id).limit(1))
    if not existing:
        for index, point in enumerate(points):
            db.add(WasteCollectionRecord(event_id=event.id, collection_point_id=point.id, waste_type_id=waste_type.id, weight_kg=Decimal("18.5") + index * Decimal("7.25"), submitter_name="Operador demo", submitter_rut="11.111.111-1", client_generated_id=uuid4(), recorded_at=datetime.now(timezone.utc), synced_at=datetime.now(timezone.utc)))


def _create_order_data(db, event: Event, zones: list[EventZone], admin: User, worker: User) -> None:
    existing = db.scalar(select(EventOrder.id).where(EventOrder.event_id == event.id).limit(1))
    if existing:
        return
    catalog = db.scalar(select(CatalogItem).where(CatalogItem.name == "Contenedor 240 litros demo"))
    if not catalog:
        catalog = CatalogItem(name="Contenedor 240 litros demo", category="Residuos", description="Contenedor para operación demo", unit="unidad", default_unit_price=Decimal("45000"), is_active=True)
        db.add(catalog)
        db.flush()
    order = EventOrder(event_id=event.id, requested_by=admin.id, assigned_to=worker.id, title="Implementación logística demo", description="Pedido completo para probar carga, entrega y retorno.", status=OrderStatus.DELIVERED, requested_date=event.start_date, required_date=event.start_date, total_amount=Decimal("180000"), notes="Datos de prueba integral.")
    db.add(order)
    db.flush()
    db.add(EventOrderItem(order_id=order.id, catalog_item_id=catalog.id, zone_id=zones[0].id, item_name_snapshot=catalog.name, quantity=Decimal("4"), unit=catalog.unit, unit_price=Decimal("45000"), total_price=Decimal("180000"), load_status=OrderItemStageStatus.COMPLETED, delivery_status=OrderItemStageStatus.COMPLETED, return_status=OrderItemStageStatus.PENDING, loaded_at=datetime.now(), delivered_at=datetime.now(), loaded_by=worker.id, delivered_by=worker.id, delivery_observation="Entrega demo confirmada."))


def _create_alert_data(db, event: Event, zones: list[EventZone]) -> None:
    existing = db.scalar(select(Alert.id).where(Alert.event_id == event.id).limit(1))
    if existing:
        return
    db.add_all([
        Alert(event_id=event.id, zone_id=zones[1].id if len(zones) > 1 else zones[0].id, title="Revisar frecuencia de retiro", description="Alerta demo abierta para revisar el acopio de público.", alert_type="WASTE", priority=PriorityLevel.HIGH, status="OPEN", generated_from="DEMO"),
        Alert(event_id=event.id, zone_id=zones[0].id, title="Medición ambiental validada", description="Alerta demo informativa cerrada.", alert_type="ENVIRONMENTAL", priority=PriorityLevel.LOW, status="CLOSED", generated_from="DEMO", closed_at=datetime.now()),
    ])


def _create_logbook_data(db, event: Event, zone: EventZone, admin: User, worker: User) -> None:
    existing = db.scalar(select(LogbookInstance.id).where(LogbookInstance.event_id == event.id).limit(1))
    if existing:
        return
    template = LogbookTemplate(name="Checklist operativo demo", description="Bitácora integral para probar asignación, respuesta y revisión.", instructions="Completa cada control durante la operación.", operational_stage=LogbookOperationalStage.OPERATION, status=LogbookTemplateStatus.ACTIVE, default_assignment_mode=LogbookAssignmentMode.INDIVIDUAL, default_client_visibility=True, created_by=admin.id)
    db.add(template)
    db.flush()
    version = LogbookTemplateVersion(template_id=template.id, version_number=1, status=LogbookVersionStatus.PUBLISHED, change_notes="Versión demo publicada.", created_by=admin.id, published_by=admin.id, published_at=datetime.now())
    db.add(version)
    db.flush()
    section = LogbookSection(template_version_id=version.id, title="Operación ambiental", description="Controles principales del evento.", position=1, is_required=True)
    db.add(section)
    db.flush()
    item = LogbookItem(section_id=section.id, title="Puntos limpios operativos", description="Verifica que los puntos estén instalados y señalizados.", instructions="Marca aprobado si están disponibles.", position=1, item_type=LogbookItemType.YES_NO, is_required=True, evidence_policy=LogbookEvidencePolicy.OPTIONAL, client_visible_by_default=True)
    db.add(item)
    db.flush()
    instance = LogbookInstance(event_id=event.id, template_id=template.id, template_version_id=version.id, name="Bitácora operación ambiental demo", operational_stage=LogbookOperationalStage.OPERATION, zone_id=zone.id, assignment_mode=LogbookAssignmentMode.INDIVIDUAL, opens_at=event.start_date, due_at=event.end_date, supervisor_id=admin.id, status=LogbookInstanceStatus.IN_PROGRESS, client_visibility=True, created_by=admin.id)
    db.add(instance)
    db.flush()
    assignment = LogbookAssignment(logbook_instance_id=instance.id, user_id=worker.id, assignment_role="PARTICIPANT", status=LogbookAssignmentStatus.APPROVED, started_at=datetime.now(), submitted_at=datetime.now(), approved_at=datetime.now(), approved_by=admin.id, attempt_number=1)
    db.add(assignment)
    db.flush()
    db.add(LogbookInstanceItem(instance_id=instance.id, title=item.title, source_row=1, position=1))
    db.add(LogbookResponse(assignment_id=assignment.id, logbook_item_id=item.id, boolean_value=True, result_status=LogbookResultStatus.COMPLETED, comment="Control demo completado.", completed_by=worker.id, completed_at=datetime.now()))


if __name__ == "__main__":
    raise SystemExit(main())
