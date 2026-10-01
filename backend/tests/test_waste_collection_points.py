from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import warnings
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, delete, select, text

from app.db.session import SessionLocal, set_rls_context
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventStaff, EventZone, User, WasteCollectionRecord, WasteRecord, WasteType
from app.models.enums import EventStatus, UserRole, WasteDestination
from app.schemas.collection_point_schema import CollectionPointCreate, PublicWasteRecordCreate
from app.schemas.waste_schema import WasteSummaryRead
from app.services import collection_point_service as service, waste_service


@pytest.fixture()
def collection_context():
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    client = Client(business_name=f"Waste point test {suffix}")
    db.add(client)
    db.flush()
    admin = User(full_name="Test Admin", email=f"waste-point-{suffix}@example.test", password_hash="x", role=UserRole.ADMIN)
    worker = User(full_name="Test Worker", email=f"waste-worker-{suffix}@example.test", password_hash="x", role=UserRole.WORKER)
    supervisor = User(full_name="Test Supervisor", email=f"waste-supervisor-{suffix}@example.test", password_hash="x", role=UserRole.SUPERVISOR)
    db.add_all([admin, worker, supervisor])
    db.flush()
    start = datetime.now(timezone.utc).replace(tzinfo=None)
    event = Event(client_id=client.id, name=f"Waste point event {suffix}", start_date=start, end_date=start + timedelta(days=1), status=EventStatus.PLANNING, created_by=admin.id)
    other = Event(client_id=client.id, name=f"Other waste event {suffix}", start_date=start, end_date=start + timedelta(days=1), status=EventStatus.PLANNING, created_by=admin.id)
    db.add_all([event, other])
    db.flush()
    db.add(EventStaff(event_id=event.id, user_id=supervisor.id))
    zone = EventZone(event_id=event.id, name="Backstage")
    foreign_zone = EventZone(event_id=other.id, name="Otra zona")
    waste_type = WasteType(name=f"Cartón {suffix}")
    db.add_all([zone, foreign_zone, waste_type])
    db.commit()
    set_rls_context(db, user_id=admin.id, role=admin.role)
    try:
        yield db, event, other, zone, foreign_zone, waste_type, admin, worker, supervisor
    finally:
        db.rollback()
        db.execute(delete(AuditLog).where(AuditLog.event_id.in_([event.id, other.id])))
        db.execute(delete(Event).where(Event.id.in_([event.id, other.id])))
        db.execute(delete(User).where(User.id.in_([admin.id, worker.id, supervisor.id])))
        db.execute(delete(WasteType).where(WasteType.id == waste_type.id))
        db.execute(delete(Client).where(Client.id == client.id))
        db.commit()
        db.close()


def _submission(waste_type_id, **overrides):
    data = {
        "client_generated_id": uuid4(), "device_id": uuid4(), "waste_type_id": waste_type_id,
        "collection_point_id": overrides.pop("collection_point_id", uuid4()),
        "weight_kg": Decimal("12.4"), "submitter_name": "Trabajador Greenway",
        "submitter_rut": "11111111-1", "recorded_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return PublicWasteRecordCreate(**data)


def _active_form(db, event, admin):
    service.read_event_form(db, event.id, admin, None)
    return service.set_event_form_status(db, event.id, admin, "ACTIVE", None)


def test_collection_point_creation_and_foreign_zone_rejected(collection_context):
    db, event, _, zone, foreign_zone, _, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Backstage", zone_id=zone.id), admin, "http://localhost:3000")
    assert point.id
    with pytest.raises(HTTPException) as error:
        service.create_point(db, event.id, CollectionPointCreate(code="AC-02", name="Food trucks", zone_id=foreign_zone.id), admin, "http://localhost:3000")
    assert error.value.status_code == 400


def test_collection_point_serialization_uses_nested_schema_models(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    point = service.create_point(
        db,
        event.id,
        CollectionPointCreate(
            code="AC-WARN",
            name="Sin advertencias",
            allowed_waste_type_ids=[waste_type.id],
        ),
        admin,
        None,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        payload = point.model_dump(mode="json")

    assert payload["allowed_waste_types"] == [{
        "id": str(waste_type.id),
        "name": waste_type.name,
        "is_recyclable": waste_type.is_recyclable,
    }]


def test_event_form_public_private_and_token_regeneration(collection_context):
    db, event, _, _, _, _, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Backstage"), admin, None)
    form = service.read_event_form(db, event.id, admin, None)
    assert form["status"] == "DRAFT"
    with pytest.raises(HTTPException):
        service.public_point(db, form["token"])
    active = service.set_event_form_status(db, event.id, admin, "ACTIVE", None)
    assert service.public_point(db, active["token"])["collection_points"][0]["id"] == point.id
    closed = service.set_event_form_status(db, event.id, admin, "CLOSED", None)
    assert closed["status"] == "CLOSED"
    assert closed["token"] == active["token"]
    with pytest.raises(HTTPException):
        service.public_point(db, closed["token"])
    reopened = service.set_event_form_status(db, event.id, admin, "ACTIVE", None)
    assert reopened["token"] == active["token"]
    regenerated = service.set_event_form_status(db, event.id, admin, "REGENERATE", None)
    assert regenerated["token"] != active["token"]
    with pytest.raises(HTTPException):
        service.public_point(db, active["token"])


def test_public_batch_partially_rejects_unknown_type_and_is_idempotent(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Backstage", allowed_waste_type_ids=[waste_type.id]), admin, None)
    form = _active_form(db, event, admin)
    first = _submission(waste_type.id, collection_point_id=point.id)
    second = _submission(uuid4(), collection_point_id=point.id)
    accepted, rejected = service.submit_public_records(db, form["token"], [first, second])
    assert len(accepted) == 1 and len(rejected) == 1
    assert isinstance(accepted[0], WasteCollectionRecord)
    assert accepted[0].collection_point_id == point.id
    assert db.scalar(select(WasteRecord.id).where(WasteRecord.event_id == event.id)) is None
    repeated, _ = service.submit_public_records(db, form["token"], [first])
    assert len(repeated) == 1 and repeated[0].id == accepted[0].id


def test_collection_records_are_included_in_general_summary(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Backstage", allowed_waste_type_ids=[waste_type.id]), admin, None)
    form = _active_form(db, event, admin)
    service.submit_public_records(db, form["token"], [_submission(waste_type.id, collection_point_id=point.id)])
    collection = service.collection_summary(db, event.id, admin)
    environmental = waste_service.get_waste_summary(db, event.id, admin)
    WasteSummaryRead.model_validate(environmental)
    assert collection["total_kg"] == Decimal("12.4")
    assert collection["records_count"] == 1
    assert environmental["total_kg"] == Decimal("12.4")
    assert environmental["total_event_kg"] == Decimal("12.4")
    assert environmental["records_count"] == 1
    assert environmental["total_records"] == 1
    assert environmental["waste_types_count"] == 1
    assert environmental["by_type"][0]["total_kg"] == Decimal("12.4")
    assert environmental["by_type"][0]["collection_points_kg"] == Decimal("12.4")
    assert environmental["by_type"][0]["direct_kg"] == Decimal("0")
    assert environmental["collection_points"] == {
        "weight_kg": Decimal("12.4"), "percentage": Decimal("100.00"), "records_count": 1
    }
    assert environmental["direct_records"]["weight_kg"] == Decimal("0")
    assert environmental["top_collection_point"]["code"] == "AC-01"
    assert environmental["top_collection_point"]["weight_kg"] == Decimal("12.4")
    db.add(WasteRecord(event_id=event.id, waste_type_id=waste_type.id, weight_kg=100, destination=WasteDestination.RECYCLING))
    db.commit()
    assert service.collection_summary(db, event.id, admin)["total_kg"] == Decimal("12.4")
    combined = waste_service.get_waste_summary(db, event.id, admin)
    WasteSummaryRead.model_validate(combined)
    assert combined["total_kg"] == Decimal("112.4")
    assert combined["records_count"] == 2
    assert combined["collection_points"]["percentage"] == Decimal("11.03")
    assert combined["direct_records"]["percentage"] == Decimal("88.97")
    assert combined["recovered_kg"] == Decimal("100")
    assert combined["by_type"][0]["total_kg"] == Decimal("112.4")
    assert combined["by_type"][0]["collection_points_kg"] == Decimal("12.4")
    assert combined["by_type"][0]["direct_kg"] == Decimal("100")
    assert combined["by_source"][0]["weight_kg"] + combined["by_source"][1]["weight_kg"] == Decimal("112.4")


def test_waste_summary_handles_zero_other_and_unassigned_zone(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    empty = waste_service.get_waste_summary(db, event.id, admin)
    WasteSummaryRead.model_validate(empty)
    assert empty["total_kg"] == Decimal("0")
    assert empty["records_count"] == 0
    assert empty["recovery_percentage"] == Decimal("0")
    assert empty["top_waste_type"] is None
    assert empty["top_collection_point"] is None
    assert empty["collection_points"]["percentage"] == Decimal("0")
    assert empty["direct_records"]["percentage"] == Decimal("0")

    db.add(WasteRecord(event_id=event.id, waste_type_id=waste_type.id, weight_kg=2, destination=WasteDestination.OTHER, zone_id=None))
    db.commit()
    summary = waste_service.get_waste_summary(db, event.id, admin)
    assert summary["total_kg"] == Decimal("2")
    assert summary["records_count"] == 1
    assert summary["recovered_kg"] == Decimal("0")
    assert summary["landfill_kg"] == Decimal("0")
    assert summary["recovery_percentage"] == Decimal("0")
    assert summary["by_destination"][0]["name"] == WasteDestination.OTHER.value
    assert summary["by_zone"][0]["name"] == "Sin zona"


def test_waste_summary_sorts_collection_points_by_received_weight(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    first = service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Backstage", allowed_waste_type_ids=[waste_type.id]), admin, None)
    second = service.create_point(db, event.id, CollectionPointCreate(code="AC-02", name="Food Trucks", allowed_waste_type_ids=[waste_type.id]), admin, None)
    form = _active_form(db, event, admin)
    service.submit_public_records(db, form["token"], [
        _submission(waste_type.id, collection_point_id=first.id, weight_kg=Decimal("5")),
        _submission(waste_type.id, collection_point_id=second.id, weight_kg=Decimal("12")),
    ])

    summary = waste_service.get_waste_summary(db, event.id, admin)
    WasteSummaryRead.model_validate(summary)
    assert [item["code"] for item in summary["by_collection_point"]] == ["AC-02", "AC-01"]
    assert summary["top_collection_point"]["collection_point_id"] == second.id
    assert summary["total_event_kg"] == Decimal("17")
    assert summary["total_records"] == 2


def test_waste_summary_orders_types_and_zones_and_groups_dispositions(collection_context):
    db, event, _, zone, _, waste_type, admin, _, _ = collection_context
    second_zone = EventZone(event_id=event.id, name="Food Trucks")
    db.add(second_zone)
    db.flush()
    db.add_all([
        WasteRecord(event_id=event.id, waste_type_id=waste_type.id, weight_kg=2, destination=WasteDestination.OTHER),
        WasteRecord(event_id=event.id, waste_type_id=waste_type.id, zone_id=zone.id, weight_kg=8, destination=WasteDestination.RECYCLING),
        WasteRecord(event_id=event.id, zone_id=second_zone.id, weight_kg=4, destination=WasteDestination.COMPOSTING),
        WasteRecord(event_id=event.id, waste_type_id=waste_type.id, zone_id=zone.id, weight_kg=6, destination=WasteDestination.LANDFILL),
        WasteRecord(event_id=event.id, weight_kg=10, destination=WasteDestination.SPECIAL_DISPOSAL),
    ])
    db.commit()

    summary = waste_service.get_waste_summary(db, event.id, admin)
    assert summary["total_kg"] == Decimal("30")
    assert summary["records_count"] == 5
    assert summary["recovered_kg"] == Decimal("12")
    assert summary["landfill_kg"] == Decimal("6")
    assert summary["special_disposal_kg"] == Decimal("10")
    assert summary["recovery_percentage"] == Decimal("40.00")
    assert [item["total_kg"] for item in summary["by_type"]] == [Decimal("16"), Decimal("14")]
    assert [item["name"] for item in summary["by_zone"]] == ["Backstage", "Food Trucks", "Sin zona"]
    assert [item["total_kg"] for item in summary["by_zone"]] == [Decimal("14"), Decimal("4"), Decimal("12")]
    assert len(summary["by_destination"]) == 5


def test_negative_weight_and_invalid_rut_rejected(collection_context):
    _, _, _, _, _, waste_type, _, _, _ = collection_context
    with pytest.raises(ValidationError):
        _submission(waste_type.id, weight_kg=Decimal("-1"))
    with pytest.raises(ValidationError):
        _submission(waste_type.id, submitter_rut="11111111-2")


def test_point_material_allowlist_and_closed_offline_cutoff(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-OFF", name="Offline", allowed_waste_type_ids=[waste_type.id]), admin, None)
    form = _active_form(db, event, admin)
    allowed = _submission(waste_type.id, collection_point_id=point.id, recorded_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    forbidden = _submission(uuid4(), collection_point_id=point.id)
    _, rejected = service.submit_public_records(db, form["token"], [forbidden])
    assert rejected[0]["reason"] == "WASTE_TYPE_NOT_ALLOWED"
    assert service.set_event_form_status(db, event.id, admin, "CLOSED", None)["status"] == "CLOSED"
    accepted, rejected = service.submit_public_records(db, form["token"], [allowed])
    assert len(accepted) == 1 and not rejected
    too_late = _submission(waste_type.id, collection_point_id=point.id, recorded_at=datetime.now(timezone.utc) + timedelta(minutes=1))
    _, rejected = service.submit_public_records(db, form["token"], [too_late])
    assert rejected[0]["reason"] == "FORM_CLOSED_AFTER_RECORD"


def test_admin_and_assigned_supervisor_can_manage_but_worker_cannot(collection_context):
    db, event, _, _, _, _, admin, worker, supervisor = collection_context
    assert service.create_point(db, event.id, CollectionPointCreate(code="AC-01", name="Admin"), admin, None).event_id == event.id
    assert service.create_point(db, event.id, CollectionPointCreate(code="AC-02", name="Supervisor"), supervisor, None).event_id == event.id
    with pytest.raises(HTTPException) as error:
        service.create_point(db, event.id, CollectionPointCreate(code="AC-03", name="Worker"), worker, None)
    assert error.value.status_code == 403


def test_public_rls_token_allows_only_scoped_point_and_record_insert(collection_context):
    db, event, _, _, _, waste_type, admin, _, _ = collection_context
    point = service.create_point(db, event.id, CollectionPointCreate(code="AC-RLS", name="RLS", allowed_waste_type_ids=[waste_type.id]), admin, None)
    form = _active_form(db, event, admin)
    rls_url = os.environ.get("RLS_DATABASE_URL")
    if not rls_url:
        pytest.skip("RLS_DATABASE_URL local sin privilegios de owner no configurado")
    engine = create_engine(rls_url)
    with engine.connect() as connection:
        rls_role = connection.scalar(text("select current_user"))
    owner_engine = create_engine(os.environ["DATABASE_URL"])
    quoted_role = owner_engine.dialect.identifier_preparer.quote(rls_role)
    with owner_engine.begin() as connection:
        connection.execute(text(f"GRANT SELECT, INSERT ON waste_collection_records TO {quoted_role}"))
        connection.execute(text(f"GRANT SELECT, INSERT, DELETE ON waste_collection_point_types TO {quoted_role}"))
    owner_engine.dispose()
    client_id = uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(text("select set_config('app.current_user_id', :value, true)"), {"value": str(admin.id)})
            connection.execute(text("select set_config('app.current_role', 'ADMIN', true)"))
            connection.execute(text("select set_config('app.current_client_id', '', true)"))
            deleted = connection.execute(text("""
                delete from waste_collection_point_types
                where collection_point_id=:point and waste_type_id=:type
            """), {"point": point.id, "type": waste_type.id})
            assert deleted.rowcount == 1
            connection.execute(text("""
                insert into waste_collection_point_types (collection_point_id, waste_type_id)
                values (:point, :type)
            """), {"point": point.id, "type": waste_type.id})
        with engine.begin() as connection:
            connection.execute(text("select set_config('app.public_waste_token', :token, true)"), {"token": form["token"]})
            visible = connection.scalar(text("select id from waste_collection_points where id=:id"), {"id": point.id})
            assert visible == point.id
            created = connection.scalar(text("""
                insert into waste_collection_records (
                    id,event_id,collection_point_id,waste_type_id,weight_kg,
                    submitter_name,submitter_rut,client_generated_id,recorded_at,synced_at
                ) values (
                    :id,:event,:point,:type,12.4,'Trabajador','11111111-1',:client,now(),now()
                ) returning id
            """), {"id": uuid4(), "event": event.id, "point": point.id, "type": waste_type.id, "client": client_id})
            assert created is not None
        with engine.begin() as connection:
            hidden = connection.scalar(text("select id from waste_collection_points where id=:id"), {"id": point.id})
            assert hidden is None
    finally:
        engine.dispose()
