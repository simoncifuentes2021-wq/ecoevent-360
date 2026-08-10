from __future__ import annotations

import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import (  # noqa: E402
    CarbonFactor,
    CarbonRecord,
    Evidence,
    Event,
    Task,
    WasteRecord,
    WasteType,
)
from app.models.enums import (  # noqa: E402
    CarbonScope,
    ReportScope,
    TaskStatus,
    WasteDestination,
)
from app.schemas.report_schema import ReportUpdate  # noqa: E402
from app.services import report_builder_service  # noqa: E402
from scripts.seed_session_comparison_demo import (  # noqa: E402
    DEMO_PREFIX,
    seed as seed_comparison,
)


def assert_disposable_database() -> None:
    parsed = urlparse(settings.database_url.replace("postgresql+psycopg://", "postgresql://"))
    database = parsed.path.lstrip("/").lower()
    if parsed.hostname not in {"localhost", "127.0.0.1"} or not any(
        token in database for token in ("test", "disposable")
    ):
        raise SystemExit(
            "BLOQUEADO: este cargador solo funciona en PostgreSQL local cuyo nombre contenga 'test' o 'disposable'."
        )
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
    assert_disposable_database()

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
            ]
        )

        evidence = Evidence(
            event_id=event.id,
            session_id=main_show.id,
            uploaded_by=admin.id,
            file_url="/uploads/demo-evidence.png",
            file_type="image/png",
            description="Evidencia principal de gestión ambiental y movilidad sostenible",
            taken_at=datetime.now(),
        )
        db.add(evidence)
        db.flush()

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
        report_builder_service.update_report(
            db,
            event_report,
            ReportUpdate(
                template_key="ENVIRONMENTAL_STORY", edit_version=event_report.edit_version
            ),
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
