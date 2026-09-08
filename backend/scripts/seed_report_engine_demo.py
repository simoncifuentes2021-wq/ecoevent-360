from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import (  # noqa: E402
    CarbonFactor,
    CarbonRecord,
    EnergyRecord,
    Evidence,
    Event,
    EventService,
    EventStaff,
    EventZone,
    FuelRecord,
    Incident,
    ReportEvidence,
    Service,
    Task,
    User,
    WaterRecord,
    WasteRecord,
    WasteType,
)
from app.models.environmental import EnvironmentalAction, EnvironmentalActionMetric  # noqa: E402
from app.models.enums import (  # noqa: E402
    CarbonScope,
    EnvironmentalActionStatus,
    EnvironmentalActionType,
    EnvironmentalEnergyInputMode,
    EnvironmentalEnergySource,
    EnvironmentalMetricKey,
    EnvironmentalReviewStatus,
    IncidentStatus,
    PriorityLevel,
    ReportScope,
    ReportLayoutVariant,
    TaskStatus,
    WasteDestination,
)
from app.schemas.report_schema import ReportUpdate  # noqa: E402
from app.services import file_storage_service, report_builder_service  # noqa: E402
from scripts.seed_session_comparison_demo import (  # noqa: E402
    DEMO_PREFIX,
    seed as seed_comparison,
)


def assert_local_database() -> None:
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg://", "postgresql://"))
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("BLOQUEADO: este fixture solo funciona contra PostgreSQL local.")
    if settings.app_env.lower() == "production":
        raise SystemExit("BLOQUEADO: APP_ENV=production.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea una base integral para probar el motor de reportes."
    )
    parser.add_argument(
        "--yes", action="store_true", help="Confirma la creación en la DB descartable."
    )
    parser.add_argument("--admin-email", default="admin@ecoevent.cl")
    args = parser.parse_args()
    if not args.yes:
        print("No se creó nada. Ejecuta con --yes.")
        return 2
    assert_local_database()

    with SessionLocal() as db:
        result = seed_comparison(db, client_id=None, admin_email=args.admin_email)
        if result:
            return result
        event = db.scalar(
            select(Event)
            .where(Event.name.startswith(DEMO_PREFIX))
            .order_by(Event.created_at.desc())
        )
        if event is None:
            raise SystemExit("No se encontró el evento demo recién creado.")
        admin = next((user for user in event.client.users if user.email == args.admin_email), None)
        if admin is None:
            from app.models.core import User

            admin = db.scalar(select(User).where(User.email == args.admin_email))
        if admin is None:
            raise SystemExit(f"No existe el usuario administrador {args.admin_email}.")

        shows = sorted(event.sessions, key=lambda item: item.sort_order)
        main_show = shows[0]
        zones = [
            EventZone(event_id=event.id, name="Escenario principal", description="Produccion, artistas y energia."),
            EventZone(event_id=event.id, name="Zona de publico", description="Accesos, experiencia y puntos limpios."),
            EventZone(event_id=event.id, name="Backstage y carga", description="Logistica, proveedores y almacenamiento."),
        ]
        db.add_all(zones)
        db.flush()

        service_rows = [
            ("Gestion integral de residuos", "Sostenibilidad", "jornada", Decimal("3"), Decimal("480000")),
            ("Torres fotovoltaicas", "Energia limpia", "torre", Decimal("4"), Decimal("350000")),
            ("Operacion Bike Zone", "Movilidad sostenible", "jornada", Decimal("3"), Decimal("260000")),
            ("Medicion de huella de carbono", "Consultoria ambiental", "informe", Decimal("1"), Decimal("950000")),
        ]
        for name, category, unit, quantity, unit_price in service_rows:
            service = db.scalar(select(Service).where(Service.name == name))
            if service is None:
                service = Service(name=name, category=category, unit=unit, base_price=unit_price, description=f"Servicio demo de {category.lower()}.")
                db.add(service)
                db.flush()
            db.add(EventService(event_id=event.id, service_id=service.id, quantity=quantity, unit_price=unit_price, total_price=quantity * unit_price, notes="Servicio confirmado y ejecutado para la demostracion."))

        staff_users = list(db.scalars(select(User).order_by(User.created_at.asc()).limit(4)).all())
        for index, user in enumerate(staff_users):
            db.add(EventStaff(event_id=event.id, user_id=user.id, role_in_event=["Direccion del evento", "Supervision ambiental", "Coordinacion logistica", "Operacion en terreno"][index], shift_start=event.start_date, shift_end=event.end_date))

        db.add_all(
            [
                Task(
                    event_id=event.id,
                    session_id=main_show.id,
                    title="Montaje de puntos limpios",
                    description="Instalación y señalización completada antes de apertura.",
                    status=TaskStatus.COMPLETED,
                    created_by=admin.id,
                ),
                Task(
                    event_id=event.id,
                    session_id=main_show.id,
                    title="Control de Bike Zone",
                    description="Registro y custodia de bicicletas durante el show.",
                    status=TaskStatus.COMPLETED,
                    created_by=admin.id,
                ),
                Task(
                    event_id=event.id,
                    title="Consolidación ambiental del evento",
                    status=TaskStatus.COMPLETED,
                    created_by=admin.id,
                ),
                Task(event_id=event.id, session_id=main_show.id, zone_id=zones[0].id, title="Verificar generacion fotovoltaica", description="Lectura de energia por torre y hora validada durante la operacion.", status=TaskStatus.COMPLETED, priority=PriorityLevel.HIGH, created_by=admin.id),
                Task(event_id=event.id, session_id=shows[1].id, zone_id=zones[1].id, title="Auditar segregacion de residuos", description="Revision de contenedores, senaletica y retiro por gestor.", status=TaskStatus.IN_PROGRESS, priority=PriorityLevel.MEDIUM, created_by=admin.id),
            ]
        )

        db.add_all([
            Incident(event_id=event.id, session_id=main_show.id, zone_id=zones[1].id, title="Saturacion puntual de contenedor PET", description="Se reemplazo el contenedor y se reforzo la frecuencia de retiro en 12 minutos.", incident_type="AMBIENTAL", status=IncidentStatus.RESOLVED, priority=PriorityLevel.MEDIUM, reported_by=admin.id, assigned_to=admin.id, resolved_at=datetime.now()),
            Incident(event_id=event.id, session_id=shows[1].id, zone_id=zones[0].id, title="Lectura irregular en medidor secundario", description="Se contrasto con el medidor principal sin perdida de suministro ni impacto al publico.", incident_type="ENERGIA", status=IncidentStatus.CLOSED, priority=PriorityLevel.LOW, reported_by=admin.id, assigned_to=admin.id, resolved_at=datetime.now(), closed_at=datetime.now()),
        ])

        db.add_all([
            EnergyRecord(event_id=event.id, source="Torres fotovoltaicas", kwh=Decimal("36"), hours_used=Decimal("12"), notes="0,75 kWh por torre/hora x 4 torres x 12 h.", recorded_by=admin.id),
            EnergyRecord(event_id=event.id, source="Red electrica recinto", kwh=Decimal("85742"), hours_used=Decimal("42"), notes="Lectura consolidada del medidor principal.", recorded_by=admin.id),
            FuelRecord(event_id=event.id, vehicle_name="Camion logistica", vehicle_plate="DEMO-01", fuel_type="Diesel", liters=Decimal("186.5"), kilometers=Decimal("742"), trips=8, recorded_by=admin.id),
            WaterRecord(event_id=event.id, source="Red potable", liters=Decimal("184500"), usage_type="Sanitarios, hidratacion y limpieza", notes="Lectura inicial y final del recinto.", recorded_by=admin.id),
        ])

        solar_action = EnvironmentalAction(
            event_id=event.id, session_id=main_show.id,
            action_type=EnvironmentalActionType.SOLAR_ENERGY,
            status=EnvironmentalActionStatus.CALCULATED,
            review_status=EnvironmentalReviewStatus.APPROVED,
            name="Torre fotovoltaica para iluminacion y carga",
            description="Cuatro torres solares sustituyeron generadores diesel en el escenario y accesos.",
            quantity_used=Decimal("4"), hours_used=Decimal("12"),
            energy_per_unit_hour_kwh=Decimal("0.75"), energy_kwh=Decimal("36"),
            energy_input_mode=EnvironmentalEnergyInputMode.PER_UNIT_HOUR,
            energy_source=EnvironmentalEnergySource.CALCULATED,
            notes="Calculo validado: 0,75 x 4 x 12 = 36 kWh.", created_by=admin.id,
        )
        db.add(solar_action)
        db.flush()
        db.add_all([
            EnvironmentalActionMetric(action_id=solar_action.id, metric_key=EnvironmentalMetricKey.ENERGY_KWH, unit="kWh", calculated_value=Decimal("36"), calculation_method="Energia por torre/hora x cantidad x horas", calculation_snapshot={"energy_per_unit_hour_kwh": 0.75, "quantity_used": 4, "hours_used": 12, "energy_kwh": 36}),
            EnvironmentalActionMetric(action_id=solar_action.id, metric_key=EnvironmentalMetricKey.CO2E_AVOIDED_KG, unit="kgCO2e", calculated_value=Decimal("31.68"), calculation_method="Comparacion con generacion diesel de referencia", calculation_snapshot={"energy_kwh": 36, "avoided_factor_kgco2e_per_kwh": 0.88}),
        ])

        evidences = []
        for index, (width, height, color) in enumerate(
            [(1200, 700, "#15803d"), (700, 1200, "#0f766e"), (900, 650, "#65a30d"), (800, 800, "#047857")],
            start=1,
        ):
            image = Image.new("RGB", (width, height), color)
            ImageDraw.Draw(image).text((40, 40), f"EcoEvent fixture v3 - evidencia {index}", fill="white")
            content = io.BytesIO()
            image.save(content, format="PNG")
            storage_key = file_storage_service.save_bytes_file(
                "report-layout-v3", content.getvalue(), content_type="image/png",
                allowed_content_types={"image/png": ".png"}, original_filename=f"fixture-{index}.png",
            )
            evidences.append(Evidence(
                event_id=event.id, session_id=main_show.id, uploaded_by=admin.id,
                file_url=storage_key, file_type="image/png",
                description=f"Fixture visual v3 {'horizontal' if width > height else 'vertical'} {index}",
                taken_at=datetime.now(),
            ))
        db.add_all(evidences)
        db.flush()
        evidence = evidences[0]

        waste_rows = [
            ("Botellas de plástico PET", Decimal("71.040"), WasteDestination.RECYCLING),
            ("Latas de aluminio", Decimal("32.930"), WasteDestination.RECYCLING),
            ("Plástico PP y PE", Decimal("21.700"), WasteDestination.RECYCLING),
            ("Vidrio", Decimal("26.100"), WasteDestination.RECYCLING),
            ("Cartón", Decimal("12.600"), WasteDestination.RECYCLING),
            ("Orgánico", Decimal("12.600"), WasteDestination.COMPOSTING),
        ]
        for name, weight, destination in waste_rows:
            waste_type = db.scalar(select(WasteType).where(WasteType.name == name))
            if waste_type is None:
                waste_type = WasteType(
                    name=name, is_recyclable=destination == WasteDestination.RECYCLING
                )
                db.add(waste_type)
                db.flush()
            db.add(
                WasteRecord(
                    event_id=event.id,
                    waste_type_id=waste_type.id,
                    weight_kg=weight,
                    destination=destination,
                    destination_detail="Gestor autorizado demo",
                    recorded_by=admin.id,
                    evidence_id=evidence.id,
                )
            )

        carbon_rows = [
            (
                "Transporte de público",
                "Viajes de asistentes",
                "pasajero-km",
                Decimal("0.105"),
                Decimal("1990476"),
            ),
            (
                "Transporte de artistas",
                "Traslados aéreos y terrestres",
                "km",
                Decimal("0.246"),
                Decimal("219919"),
            ),
            ("Energía", "Electricidad del recinto", "kWh", Decimal("0.128"), Decimal("85742")),
        ]
        for category, name, unit, factor_value, activity in carbon_rows:
            factor = CarbonFactor(
                category=category,
                name=name,
                unit=unit,
                factor_kgco2e=factor_value,
                scope=CarbonScope.SCOPE_3,
                source="Factor demostrativo para pruebas locales",
                year=2026,
                country="Chile",
            )
            db.add(factor)
            db.flush()
            db.add(
                CarbonRecord(
                    event_id=event.id,
                    factor_id=factor.id,
                    category=category,
                    description=f"Impacto de {name.lower()} durante el evento.",
                    activity_value=activity,
                    activity_unit=unit,
                    emissions_kgco2e=activity * factor_value,
                    recorded_by=admin.id,
                )
            )
        db.commit()

        event_report = report_builder_service.create_draft(
            db, event.id, ReportScope.EVENT, None, admin
        )
        for section in event_report.sections:
            if section.section_key == "waste":
                section.layout_variant = ReportLayoutVariant.FEATURE_CHART
                content = dict(section.content or {})
                content["items"] = [
                    {**item, "value": float(item.get("total_kg") or item.get("weight_kg") or 0)}
                    for item in (content.get("items") or [])
                ]
                section.content = content
            if section.section_key == "evidences":
                section.is_enabled = True
                section.layout_variant = ReportLayoutVariant.PHOTO_GRID
            if section.section_key == "forms":
                section.is_enabled = True
                section.layout_variant = ReportLayoutVariant.FEATURE_CHART
                content = dict(section.content or {})
                content["items"] = [
                    {"label": "Excelente", "value": 18},
                    {"label": "Bueno", "value": 11},
                    {"label": "Regular", "value": 4},
                ]
                section.content = content
        report_builder_service.update_report(
            db,
            event_report,
            ReportUpdate(
                template_key="ENVIRONMENTAL_STORY", edit_version=event_report.edit_version
            ),
        )
        evidence_section = next(
            (section for section in event_report.sections if section.section_key == "evidences"), None
        )
        db.add_all(
            [
                ReportEvidence(
                    report_id=event_report.id,
                    section_id=evidence_section.id if evidence_section else None,
                    evidence_id=item.id,
                    sort_order=index,
                    caption=item.description,
                )
                for index, item in enumerate(evidences)
            ]
        )
        show_report = report_builder_service.create_draft(
            db, event.id, ReportScope.SHOW, main_show.id, admin
        )
        report_builder_service.update_report(
            db,
            show_report,
            ReportUpdate(template_key="COMPLETE", edit_version=show_report.edit_version),
        )
        db.commit()

        print("\nMotor de reportes demo listo.")
        print(f"event_id: {event.id}")
        print(f"EVENT report_id: {event_report.id}")
        print(f"SHOW report_id: {show_report.id} ({main_show.name})")
        print("Abre http://localhost:3000/reports para crear o continuar reportes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
