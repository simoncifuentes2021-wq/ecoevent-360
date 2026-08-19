from datetime import datetime, timedelta
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import SessionLocal, set_rls_context
from app.models.audit_log import AuditLog
from app.models.core import Client, Event, EventSession, EventStaff, User
from app.models.environmental import (
    EcoEquivalenceFactor,
    EnvironmentalFactor,
    EnvironmentalMethodology,
)
from app.models.enums import (
    EnvironmentalActionStatus,
    EnvironmentalActionType,
    EnvironmentalMetricKey,
    EnvironmentalReviewDecision,
    EnvironmentalReviewStatus,
    EventStatus,
    UserRole,
)
from app.schemas.environmental_schema import (
    EcoEquivalenceCreate,
    EcoEquivalenceUpdate,
    EnvironmentalActionCreate,
    EnvironmentalActionUpdate,
    EnvironmentalReviewRequest,
    MetricOverride,
)
from app.services import environmental_calculation_service as service
from app.services import environmental_catalog_service as catalog


@pytest.fixture()
def context():
    db = SessionLocal()
    suffix = uuid4().hex[:8]
    client_a, client_b = (
        Client(business_name=f"Impact A {suffix}"),
        Client(business_name=f"Impact B {suffix}"),
    )
    db.add_all([client_a, client_b])
    db.flush()
    admin = User(
        full_name="Admin",
        email=f"impact-admin-{suffix}@test.invalid",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    supervisor = User(
        full_name="Supervisor",
        email=f"impact-supervisor-{suffix}@test.invalid",
        password_hash="x",
        role=UserRole.SUPERVISOR,
    )
    client_user = User(
        full_name="Client",
        email=f"impact-client-{suffix}@test.invalid",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=client_a.id,
    )
    foreign_client = User(
        full_name="Foreign",
        email=f"impact-foreign-{suffix}@test.invalid",
        password_hash="x",
        role=UserRole.CLIENT,
        client_id=client_b.id,
    )
    db.add_all([admin, supervisor, client_user, foreign_client])
    db.flush()
    start = datetime(2026, 8, 1)
    event = Event(
        client_id=client_a.id,
        name="Impact Event",
        start_date=start,
        end_date=start + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    other = Event(
        client_id=client_b.id,
        name="Other Event",
        start_date=start,
        end_date=start + timedelta(days=2),
        status=EventStatus.PLANNING,
        created_by=admin.id,
    )
    db.add_all([event, other])
    db.flush()
    show = EventSession(event_id=event.id, name="Show A")
    other_show = EventSession(event_id=other.id, name="Show B")
    db.add_all([show, other_show, EventStaff(event_id=event.id, user_id=supervisor.id)])
    db.commit()
    set_rls_context(db, user_id=admin.id, role=admin.role)
    baseline = EnvironmentalFactor(
        impact_type="CO2E",
        technology="Diesel tower",
        unit_basis="EQUIPMENT_HOUR",
        factor_value=Decimal("0.1"),
        factor_unit="kgCO2e/equipment-hour",
        source="Test documented source",
        year=2026,
        methodology="Test-only factor",
    )
    actual = EnvironmentalFactor(
        impact_type="CO2E",
        technology="Electric tower",
        unit_basis="ENERGY_KWH",
        factor_value=Decimal("0.05"),
        factor_unit="kgCO2e/kWh",
        source="Test documented source",
        year=2026,
        methodology="Test-only factor",
    )
    db.add_all([baseline, actual])
    db.flush()
    methodology = EnvironmentalMethodology(
        name="Tower comparison",
        action_type=EnvironmentalActionType.ELECTRIC_LIGHTING_TOWER,
        baseline_technology="Diesel tower",
        actual_technology="Electric tower",
        description="Documented test comparison",
        parameters={
            "metrics": {
                "CO2E": {
                    "baseline_factor_id": str(baseline.id),
                    "actual_factor_id": str(actual.id),
                    "baseline_basis": "EQUIPMENT_HOUR",
                    "actual_basis": "ENERGY_KWH",
                }
            }
        },
    )
    db.add(methodology)
    db.commit()
    try:
        yield (
            db,
            event,
            other,
            show,
            other_show,
            admin,
            supervisor,
            client_user,
            foreign_client,
            methodology,
            baseline,
        )
    finally:
        set_rls_context(db, user_id=admin.id, role=admin.role)
        db.execute(delete(AuditLog).where(AuditLog.event_id.in_([event.id, other.id])))
        db.execute(delete(Event).where(Event.id.in_([event.id, other.id])))
        db.execute(
            delete(EnvironmentalMethodology).where(EnvironmentalMethodology.id == methodology.id)
        )
        db.execute(
            delete(EnvironmentalFactor).where(EnvironmentalFactor.id.in_([baseline.id, actual.id]))
        )
        db.execute(
            delete(User).where(
                User.id.in_([admin.id, supervisor.id, client_user.id, foreign_client.id])
            )
        )
        db.execute(delete(Client).where(Client.id.in_([client_a.id, client_b.id])))
        db.commit()
        db.close()


def tower_payload(methodology_id, **changes):
    values = dict(
        action_type=EnvironmentalActionType.ELECTRIC_LIGHTING_TOWER,
        methodology_id=methodology_id,
        name="Electric towers",
        quantity_used=Decimal("2"),
        hours_used=Decimal("10"),
        power_kw=Decimal("1"),
    )
    values.update(changes)
    return EnvironmentalActionCreate(**values)


def test_event_show_scope_cross_event_and_validation(context):
    db, event, _, show, other_show, admin, supervisor, *_rest = context
    event_action = service.create_action(db, event.id, tower_payload(_rest[-2].id), admin)
    show_action = service.create_action(
        db,
        event.id,
        tower_payload(_rest[-2].id, session_id=show.id, name="Show towers"),
        supervisor,
    )
    assert event_action.session_id is None and show_action.session_id == show.id
    assert (
        event_action.energy_kwh == Decimal("20")
        and event_action.energy_source.value == "CALCULATED"
    )
    with pytest.raises(HTTPException, match="does not belong"):
        service.create_action(
            db, event.id, tower_payload(_rest[-2].id, session_id=other_show.id), admin
        )
    with pytest.raises(ValueError):
        EnvironmentalActionCreate(action_type="OTHER", name="Bad", quantity_used=0)
    with pytest.raises(ValueError):
        EnvironmentalActionCreate(action_type="OTHER", name="Bad", quantity_used=-1)
    with pytest.raises(ValueError):
        EnvironmentalActionCreate(action_type="OTHER", name="Bad", quantity_used=1, hours_used=-1)


def test_baseline_actual_snapshot_precision_summary_and_factor_history(context):
    db, event, _, show, _, admin, _, _, _, methodology, baseline = context
    action = service.create_action(
        db, event.id, tower_payload(methodology.id, session_id=show.id), admin
    )
    calculated = service.calculate(db, event.id, action.id, admin)
    metrics = {m.metric_key: m for m in calculated.metrics}
    assert metrics[EnvironmentalMetricKey.ENERGY_KWH].value == Decimal("20")
    assert metrics[EnvironmentalMetricKey.CO2E_BASELINE_KG].value == Decimal("2.00000000")
    assert metrics[EnvironmentalMetricKey.CO2E_ACTUAL_KG].value == Decimal("1.00000000")
    assert metrics[EnvironmentalMetricKey.CO2E_AVOIDED_KG].value == Decimal("1.00000000")
    assert EnvironmentalMetricKey.PM25_AVOIDED_KG not in metrics
    frozen = metrics[EnvironmentalMetricKey.CO2E_AVOIDED_KG].calculation_snapshot
    baseline.factor_value = Decimal("0.2")
    db.commit()
    db.refresh(calculated)
    assert metrics[EnvironmentalMetricKey.CO2E_AVOIDED_KG].value == Decimal("1.00000000")
    assert Decimal(frozen["factors"][0]["factor_value"]) == Decimal("0.1")
    summary = service.summary(db, event.id, show.id, admin)
    assert summary.actions_count == 1 and summary.co2e_avoided_kg == Decimal("1.00000000")
    assert (
        summary.pm25_avoided_kg is None
        and EnvironmentalMetricKey.PM25_AVOIDED_KG in summary.unavailable_metrics
    )


def test_seeded_lighting_methodology_calculates_all_documented_metrics(context):
    db, event, _, _, _, admin, *_rest = context
    methodology = db.scalar(
        select(EnvironmentalMethodology).where(
            EnvironmentalMethodology.name == "Torre diésel vs torre eléctrica (energía medida)"
        )
    )
    assert methodology is not None
    action = service.create_action(
        db,
        event.id,
        EnvironmentalActionCreate(
            action_type=EnvironmentalActionType.ELECTRIC_LIGHTING_TOWER,
            methodology_id=methodology.id,
            name="Torre eléctrica verificación catálogo",
            quantity_used=Decimal("1"),
            energy_kwh=Decimal("30"),
            energy_source="MEASURED",
        ),
        admin,
    )
    calculated = service.calculate(db, event.id, action.id, admin)
    values = {metric.metric_key: metric.value for metric in calculated.metrics}
    assert values[EnvironmentalMetricKey.CO2E_BASELINE_KG] == Decimal("27.10000000")
    assert values[EnvironmentalMetricKey.CO2E_ACTUAL_KG] == Decimal("6.06300000")
    assert values[EnvironmentalMetricKey.CO2E_AVOIDED_KG] == Decimal("21.03700000")
    assert values[EnvironmentalMetricKey.FUEL_AVOIDED_L] == Decimal("10.00000000")
    assert values[EnvironmentalMetricKey.PM25_AVOIDED_KG] == Decimal("0.04023000")
    assert values[EnvironmentalMetricKey.PM10_AVOIDED_KG] == Decimal("0.04023000")
    assert values[EnvironmentalMetricKey.NOX_AVOIDED_KG] == Decimal("0.56724000")
    summary = service.summary(db, event.id, None, admin)
    equivalences = {item.key: item for item in summary.equivalences}
    assert equivalences["GASOLINE_LITERS"].source_value == Decimal("21.03700000")
    assert equivalences["GASOLINE_LITERS"].value == Decimal("8.943748016900000000")
    assert equivalences["FOREST_ACRE_YEAR"].value == Decimal("0.021037000000000000")


def test_permissions_missing_methodology_update_delete_and_override(context):
    db, event, _, _, _, admin, supervisor, client_user, foreign_client, methodology, _ = context
    pending = service.create_action(
        db,
        event.id,
        EnvironmentalActionCreate(action_type="OTHER", name="Unconfigured", quantity_used=1),
        admin,
    )
    assert (
        service.calculate(db, event.id, pending.id, admin).status
        == EnvironmentalActionStatus.MISSING_METHODOLOGY
    )
    action = service.calculate(
        db,
        event.id,
        service.create_action(
            db,
            event.id,
            tower_payload(
                methodology.id, energy_kwh=Decimal("3"), power_kw=None, energy_source="MEASURED"
            ),
            supervisor,
        ).id,
        supervisor,
    )
    metric = next(
        m for m in action.metrics if m.metric_key == EnvironmentalMetricKey.CO2E_AVOIDED_KG
    )
    with pytest.raises(HTTPException, match="administrators"):
        service.override_metric(
            db,
            event.id,
            action.id,
            metric.id,
            MetricOverride(reported_value=2, override_reason="Reviewed source"),
            supervisor,
        )
    overridden = service.override_metric(
        db,
        event.id,
        action.id,
        metric.id,
        MetricOverride(reported_value=Decimal("2.5"), override_reason="Reviewed source"),
        admin,
    )
    assert (
        overridden.value == Decimal("2.5")
        and overridden.calculated_value != overridden.reported_value
    )
    assert service.list_actions(db, event.id, None, client_user)[0] == []
    with pytest.raises(HTTPException, match="authorized"):
        service.list_actions(db, event.id, None, foreign_client)
    service.update_action(
        db, event.id, pending.id, EnvironmentalActionUpdate(name="Updated"), admin
    )
    service.delete_action(db, event.id, pending.id, admin)


def test_review_workflow_permissions_history_client_visibility_and_invalidation(context):
    db, event, _, _, _, admin, supervisor, client_user, _, methodology, _ = context
    action = service.create_action(db, event.id, tower_payload(methodology.id), supervisor)
    with pytest.raises(HTTPException, match="calculated"):
        service.submit_review(db, event.id, action.id, supervisor)
    action = service.calculate(db, event.id, action.id, supervisor)
    action = service.submit_review(db, event.id, action.id, supervisor)
    assert action.review_status == EnvironmentalReviewStatus.IN_REVIEW
    with pytest.raises(HTTPException, match="administrators"):
        service.review_action(
            db,
            event.id,
            action.id,
            EnvironmentalReviewRequest(decision=EnvironmentalReviewDecision.APPROVED),
            supervisor,
        )
    action = service.review_action(
        db,
        event.id,
        action.id,
        EnvironmentalReviewRequest(
            decision=EnvironmentalReviewDecision.APPROVED,
            comment="Fuentes y cálculo verificados",
        ),
        admin,
    )
    assert action.review_status == EnvironmentalReviewStatus.APPROVED
    assert len(service.list_actions(db, event.id, None, client_user)[0]) == 1
    history = service.review_history(db, event.id, action.id, admin)
    assert [entry["decision"] for entry in history] == [
        EnvironmentalReviewDecision.APPROVED,
        EnvironmentalReviewDecision.SUBMITTED,
    ]
    action = service.update_action(
        db,
        event.id,
        action.id,
        EnvironmentalActionUpdate(notes="Nueva evidencia operacional"),
        supervisor,
    )
    assert action.review_status == EnvironmentalReviewStatus.DRAFT
    assert action.review_revision == 2
    assert service.list_actions(db, event.id, None, client_user)[0] == []
    history = service.review_history(db, event.id, action.id, admin)
    assert history[0]["decision"] == EnvironmentalReviewDecision.INVALIDATED


def _rls_query(user, sql, params=None):
    engine = create_engine(os.environ["RLS_DATABASE_URL"])
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text("select set_config('app.current_user_id', :v, true)"), {"v": str(user.id)}
            )
            connection.execute(
                text("select set_config('app.current_role', :v, true)"), {"v": user.role.value}
            )
            connection.execute(
                text("select set_config('app.current_client_id', :v, true)"),
                {"v": str(user.client_id or "")},
            )
            result = connection.execute(text(sql), params or {})
            rows = result.fetchall() if result.returns_rows else result.rowcount
            transaction.rollback()
            return rows
        except DBAPIError:
            transaction.rollback()
            return None
        finally:
            engine.dispose()


def test_environmental_rls_client_isolation_and_write_matrix(context):
    db, event, _, _, _, admin, supervisor, client_user, foreign_client, methodology, _ = context
    action = service.create_action(db, event.id, tower_payload(methodology.id), admin)
    query = "select id from environmental_actions where id=:id"
    assert len(_rls_query(client_user, query, {"id": action.id})) == 1
    assert _rls_query(foreign_client, query, {"id": action.id}) == []
    inserted = _rls_query(
        supervisor,
        "insert into environmental_actions (event_id, action_type, name, quantity_used, created_by) values (:event_id, 'OTHER', 'RLS supervisor', 1, :user_id) returning id",
        {"event_id": event.id, "user_id": supervisor.id},
    )
    assert inserted and len(inserted) == 1
    denied = _rls_query(
        client_user,
        "insert into environmental_actions (event_id, action_type, name, quantity_used, created_by) values (:event_id, 'OTHER', 'RLS client', 1, :user_id) returning id",
        {"event_id": event.id, "user_id": client_user.id},
    )
    assert denied is None


def test_factor_metric_compatibility_and_documented_equivalence(context):
    db, event, _, _, _, admin, _, _, _, methodology, _ = context
    actual_id = methodology.parameters["metrics"]["CO2E"]["actual_factor_id"]
    actual = db.get(EnvironmentalFactor, actual_id)
    actual.impact_type = "PM25"
    db.commit()
    action = service.create_action(db, event.id, tower_payload(methodology.id), admin)
    with pytest.raises(HTTPException, match="incompatible with metric CO2E"):
        service.calculate(db, event.id, action.id, admin)
    equivalence = catalog.create_equivalence(
        db,
        EcoEquivalenceCreate(
            key="TEST_DOCUMENTED_EQUIVALENCE",
            name="Documented test equivalence",
            metric_source=EnvironmentalMetricKey.CO2E_AVOIDED_KG,
            factor=Decimal("1.25"),
            unit="test-unit",
            source="Documented test source",
            year=2026,
        ),
    )
    updated = catalog.update_equivalence(db, equivalence.id, EcoEquivalenceUpdate(is_active=False))
    assert updated.is_active is False
    db.execute(delete(EcoEquivalenceFactor).where(EcoEquivalenceFactor.id == equivalence.id))
    db.commit()
