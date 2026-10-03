"""Create a guarded demo fixture in the local disposable PostgreSQL database only."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import func, select

from app.core.database_safety import require_disposable_database
from app.core.security import hash_password
from app.db.session import SessionLocal, set_rls_context
from app.models.core import Client, Event, EventZone, User, WasteCollectionPoint, WasteCollectionRecord, WasteRecord, WasteType
from app.models.enums import EventStatus, UserRole, WasteDestination
from app.services.collection_point_service import create_point
from app.schemas.collection_point_schema import CollectionPointCreate


DEMO_DB_NAME = "ecoevent360_test"
DEMO_EMAIL = "demo.admin@ecoevent.local"
DEMO_PASSWORD = "LocalDemo-123!"
EVENT_NAME = "Festival Greenway Test"
MATERIALS = ("Cartón", "PET", "Vidrio", "Aluminio", "Orgánico", "General")
POINTS = (
    ("AC-01", "Backstage", "Backstage"),
    ("AC-02", "Food Trucks", "Food Trucks"),
    ("AC-03", "Acceso Norte", "Acceso Norte"),
)


def _assert_local_demo_database() -> None:
    identity = require_disposable_database()
    parsed = urlparse(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1))
    if identity["host"] not in {"127.0.0.1", "localhost"} or parsed.port != 5434 or identity["database"] != DEMO_DB_NAME:
        raise RuntimeError("Seed refused: target must be 127.0.0.1:5434/ecoevent360_test")


def main() -> None:
    _assert_local_demo_database()
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(func.lower(User.email) == DEMO_EMAIL.lower()))
        if admin is None:
            admin = User(
                full_name="Administrador Demo Local",
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.flush()

        set_rls_context(db, user_id=admin.id, role=admin.role, client_id=admin.client_id)
        client = db.scalar(select(Client).where(Client.business_name == "Greenway Demo Local"))
        if client is None:
            client = Client(business_name="Greenway Demo Local")
            db.add(client)
            db.flush()

        event = db.scalar(select(Event).where(Event.name == EVENT_NAME, Event.client_id == client.id))
        if event is None:
            start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            event = Event(
                client_id=client.id, name=EVENT_NAME, event_type="Festival",
                description="Datos locales de prueba para el módulo de acopios Greenway.",
                location_name="Recinto de prueba", city="Santiago", country="Chile",
                start_date=start, end_date=start + timedelta(days=1),
                status=EventStatus.IN_PROGRESS, created_by=admin.id,
            )
            db.add(event)
            db.flush()

        zones: dict[str, EventZone] = {}
        for _, _, zone_name in POINTS:
            zone = db.scalar(select(EventZone).where(EventZone.event_id == event.id, EventZone.name == zone_name))
            if zone is None:
                zone = EventZone(event_id=event.id, name=zone_name)
                db.add(zone)
                db.flush()
            zones[zone_name] = zone

        materials: dict[str, WasteType] = {}
        for material in MATERIALS:
            waste_type = db.scalar(select(WasteType).where(func.lower(WasteType.name) == material.lower()))
            if waste_type is None:
                waste_type = WasteType(name=material, is_recyclable=material != "General")
                db.add(waste_type)
                db.flush()
            materials[material] = waste_type

        db.commit()
        existing_codes = set(db.scalars(select(WasteCollectionPoint.code).where(WasteCollectionPoint.event_id == event.id)).all())
        for code, name, zone_name in POINTS:
            if code not in existing_codes:
                created = create_point(
                    db, event.id,
                    CollectionPointCreate(code=code, name=name, zone_id=zones[zone_name].id),
                    admin, "http://localhost:3000",
                )
                print(f"{created.code}: {created.public_url}")
        points = {point.code: point for point in db.scalars(select(WasteCollectionPoint).where(WasteCollectionPoint.event_id == event.id)).all()}
        now = datetime.now(timezone.utc)
        collection_samples = (
            ("AC-01", "Cartón", Decimal("12"), "Persona Demo Uno", "11111111-1"),
            ("AC-02", "PET", Decimal("8"), "Persona Demo Dos", "20927130-3"),
        )
        for code, material, weight, name, rut in collection_samples:
            exists = db.scalar(select(WasteCollectionRecord.id).where(
                WasteCollectionRecord.event_id == event.id,
                WasteCollectionRecord.collection_point_id == points[code].id,
                WasteCollectionRecord.waste_type_id == materials[material].id,
                WasteCollectionRecord.submitter_name == name,
            ).limit(1))
            if not exists:
                db.add(WasteCollectionRecord(
                    event_id=event.id, collection_point_id=points[code].id,
                    waste_type_id=materials[material].id, weight_kg=weight,
                    submitter_name=name, submitter_rut=rut, client_generated_id=uuid4(),
                    device_id=uuid4(), recorded_at=now, synced_at=now,
                ))
        environmental_samples = (
            ("Cartón", Decimal("100"), WasteDestination.RECYCLING),
            ("General", Decimal("40"), WasteDestination.LANDFILL),
        )
        for material, weight, destination in environmental_samples:
            exists = db.scalar(select(WasteRecord.id).where(
                WasteRecord.event_id == event.id, WasteRecord.waste_type_id == materials[material].id,
                WasteRecord.weight_kg == weight, WasteRecord.destination == destination,
            ).limit(1))
            if not exists:
                db.add(WasteRecord(
                    event_id=event.id, waste_type_id=materials[material].id,
                    weight_kg=weight, destination=destination, recorded_at=datetime.now(),
                ))
        db.commit()
        print(f"Event: {EVENT_NAME} ({event.id})")
        print(f"Login local: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("Seed applied in the disposable local database only.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
