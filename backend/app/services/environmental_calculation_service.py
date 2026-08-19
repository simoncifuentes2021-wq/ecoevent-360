from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import can_access_event, can_manage_event
from app.models.core import Event, EventSession, User
from app.models.environmental import (
    EcoEquivalenceFactor,
    EnvironmentalAction,
    EnvironmentalActionMetric,
    EnvironmentalActionReview,
    EnvironmentalFactor,
    EnvironmentalMethodology,
)
from app.models.enums import (
    EnvironmentalActionStatus,
    EnvironmentalEnergySource,
    EnvironmentalMetricKey,
    EnvironmentalReviewDecision,
    EnvironmentalReviewStatus,
    UserRole,
)
from app.schemas.environmental_schema import (
    EnvironmentalActionCreate,
    EnvironmentalActionUpdate,
    EnvironmentalReviewRequest,
    EnvironmentalSummary,
    MetricOverride,
)

ZERO = Decimal("0")
METRIC_UNITS = {key: "kg" for key in EnvironmentalMetricKey}
METRIC_UNITS[EnvironmentalMetricKey.ENERGY_KWH] = "kWh"
METRIC_UNITS[EnvironmentalMetricKey.FUEL_AVOIDED_L] = "L"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _event(db: Session, event_id: UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _view(db: Session, event_id: UUID, user: User) -> Event:
    event = _event(db, event_id)
    if not can_access_event(user, event_id, db):
        raise HTTPException(status_code=403, detail="Not authorized for this event")
    return event


def _manage(db: Session, event_id: UUID, user: User) -> Event:
    event = _event(db, event_id)
    if user.role not in {
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
        UserRole.SUPERVISOR,
    } or not can_manage_event(user, event_id, db):
        raise HTTPException(status_code=403, detail="Not authorized to manage environmental impact")
    return event


def _session(db: Session, event_id: UUID, session_id: UUID | None) -> None:
    if session_id is None:
        return
    item = db.scalar(
        select(EventSession).where(EventSession.id == session_id, EventSession.event_id == event_id)
    )
    if item is None:
        raise HTTPException(
            status_code=422, detail="Session does not exist or does not belong to this event"
        )
    if item.archived_at is not None:
        raise HTTPException(
            status_code=422, detail="Archived sessions cannot receive environmental actions"
        )


def _methodology(
    db: Session, methodology_id: UUID | None, action_type
) -> EnvironmentalMethodology | None:
    if methodology_id is None:
        return None
    item = db.get(EnvironmentalMethodology, methodology_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=422, detail="Active methodology not found")
    if item.action_type != action_type:
        raise HTTPException(status_code=422, detail="Methodology is incompatible with action type")
    return item


def _status(action: EnvironmentalAction) -> EnvironmentalActionStatus:
    if action.methodology_id is None:
        return EnvironmentalActionStatus.MISSING_METHODOLOGY
    if (
        action.action_type.value == "ELECTRIC_LIGHTING_TOWER"
        and action.energy_kwh is None
        and (action.hours_used is None or action.power_kw is None)
    ):
        return EnvironmentalActionStatus.INCOMPLETE
    return EnvironmentalActionStatus.READY_TO_CALCULATE


def create_action(
    db: Session, event_id: UUID, payload: EnvironmentalActionCreate, user: User
) -> EnvironmentalAction:
    _manage(db, event_id, user)
    _session(db, event_id, payload.session_id)
    _methodology(db, payload.methodology_id, payload.action_type)
    values = payload.model_dump()
    if (
        values["energy_kwh"] is None
        and values["power_kw"] is not None
        and values["hours_used"] is not None
    ):
        values["energy_kwh"] = values["quantity_used"] * values["power_kw"] * values["hours_used"]
        values["energy_source"] = EnvironmentalEnergySource.CALCULATED
    action = EnvironmentalAction(event_id=event_id, created_by=user.id, **values)
    action.status = _status(action)
    db.add(action)
    db.commit()
    db.refresh(action)
    return get_action(db, event_id, action.id, user)


def get_action(db: Session, event_id: UUID, action_id: UUID, user: User) -> EnvironmentalAction:
    _view(db, event_id, user)
    item = db.scalar(
        select(EnvironmentalAction)
        .execution_options(populate_existing=True)
        .options(selectinload(EnvironmentalAction.metrics))
        .where(EnvironmentalAction.id == action_id, EnvironmentalAction.event_id == event_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Environmental action not found")
    if user.role == UserRole.CLIENT and item.review_status != EnvironmentalReviewStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Environmental action not found")
    return item


def list_actions(
    db: Session, event_id: UUID, session_id: UUID | None, user: User
) -> tuple[list[EnvironmentalAction], int]:
    _view(db, event_id, user)
    _session(db, event_id, session_id)
    filters = [EnvironmentalAction.event_id == event_id]
    if user.role == UserRole.CLIENT:
        filters.append(EnvironmentalAction.review_status == EnvironmentalReviewStatus.APPROVED)
    if session_id is not None:
        filters.append(EnvironmentalAction.session_id == session_id)
    query = (
        select(EnvironmentalAction)
        .options(selectinload(EnvironmentalAction.metrics))
        .where(*filters)
        .order_by(EnvironmentalAction.updated_at.desc())
    )
    items = list(db.scalars(query).unique().all())
    return items, len(items)


def update_action(
    db: Session, event_id: UUID, action_id: UUID, payload: EnvironmentalActionUpdate, user: User
) -> EnvironmentalAction:
    _manage(db, event_id, user)
    item = get_action(db, event_id, action_id, user)
    _invalidate_review(db, item, user, "Datos operacionales o metodología modificados")
    values = payload.model_dump(exclude_unset=True)
    resulting_type = values.get("action_type", item.action_type)
    if "session_id" in values:
        _session(db, event_id, values["session_id"])
    if "methodology_id" in values or "action_type" in values:
        _methodology(db, values.get("methodology_id", item.methodology_id), resulting_type)
    for key, value in values.items():
        setattr(item, key, value)
    if item.energy_kwh is None and item.power_kw is not None and item.hours_used is not None:
        item.energy_kwh = item.quantity_used * item.power_kw * item.hours_used
        item.energy_source = EnvironmentalEnergySource.CALCULATED
    db.execute(
        delete(EnvironmentalActionMetric).where(EnvironmentalActionMetric.action_id == item.id)
    )
    item.status = _status(item)
    item.updated_at = _utcnow()
    db.commit()
    return get_action(db, event_id, action_id, user)


def delete_action(db: Session, event_id: UUID, action_id: UUID, user: User) -> None:
    _manage(db, event_id, user)
    item = get_action(db, event_id, action_id, user)
    db.delete(item)
    db.commit()


def _activity(action: EnvironmentalAction, basis: str) -> Decimal | None:
    values = {
        "ENERGY_KWH": action.energy_kwh,
        "DISTANCE_KM": action.distance_km,
        "HOURS": action.hours_used,
        "QUANTITY": action.quantity_used,
    }
    if basis == "EQUIPMENT_HOUR":
        return action.quantity_used * action.hours_used if action.hours_used is not None else None
    if basis == "UNIT_DISTANCE":
        return action.quantity_used * action.distance_km if action.distance_km is not None else None
    return values.get(basis)


def _factor(db: Session, raw_id: str | None) -> EnvironmentalFactor | None:
    if not raw_id:
        return None
    try:
        factor_id = UUID(raw_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid factor reference")
    factor = db.get(EnvironmentalFactor, factor_id)
    if factor is None or not factor.is_active:
        raise HTTPException(status_code=422, detail="Configured factor is missing or inactive")
    return factor


def _snapshot(action, methodology, factors, inputs):
    return {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "action_type": action.action_type.value,
        "inputs": {k: str(v) if isinstance(v, Decimal) else v for k, v in inputs.items()},
        "methodology": {
            "id": str(methodology.id),
            "name": methodology.name,
            "baseline_technology": methodology.baseline_technology,
            "actual_technology": methodology.actual_technology,
            "description": methodology.description,
            "parameters": methodology.parameters,
        },
        "factors": [
            {
                "id": str(f.id),
                "impact_type": f.impact_type,
                "technology": f.technology,
                "unit_basis": f.unit_basis,
                "factor_value": str(f.factor_value),
                "factor_unit": f.factor_unit,
                "source": f.source,
                "year": f.year,
                "methodology": f.methodology,
            }
            for f in factors
        ],
    }


def calculate(db: Session, event_id: UUID, action_id: UUID, user: User) -> EnvironmentalAction:
    _manage(db, event_id, user)
    action = get_action(db, event_id, action_id, user)
    _invalidate_review(db, action, user, "Cálculo regenerado")
    methodology = _methodology(db, action.methodology_id, action.action_type)
    if methodology is None:
        action.status = EnvironmentalActionStatus.MISSING_METHODOLOGY
        db.commit()
        return action
    produced: list[
        tuple[EnvironmentalMetricKey, Decimal, str, list[EnvironmentalFactor], dict]
    ] = []
    inputs = {
        "quantity_used": action.quantity_used,
        "hours_used": action.hours_used,
        "distance_km": action.distance_km,
        "energy_kwh": action.energy_kwh,
        "power_kw": action.power_kw,
        "energy_source": action.energy_source.value if action.energy_source else None,
    }
    if action.energy_kwh is not None:
        produced.append(
            (
                EnvironmentalMetricKey.ENERGY_KWH,
                action.energy_kwh,
                "Recorded operational energy",
                [],
                inputs,
            )
        )
    for impact, config in methodology.parameters.get("metrics", {}).items():
        try:
            baseline_key = EnvironmentalMetricKey(f"{impact}_BASELINE_KG")
            actual_key = EnvironmentalMetricKey(f"{impact}_ACTUAL_KG")
            avoided_key = EnvironmentalMetricKey(f"{impact}_AVOIDED_KG")
        except ValueError:
            continue
        baseline_factor = _factor(db, config.get("baseline_factor_id"))
        actual_factor = _factor(db, config.get("actual_factor_id"))
        if baseline_factor is None or actual_factor is None:
            continue
        if baseline_factor.impact_type != impact or actual_factor.impact_type != impact:
            raise HTTPException(
                status_code=422,
                detail=f"Configured factors are incompatible with metric {impact}",
            )
        baseline_activity = _activity(
            action, config.get("baseline_basis", baseline_factor.unit_basis)
        )
        actual_activity = _activity(action, config.get("actual_basis", actual_factor.unit_basis))
        if baseline_activity is None or actual_activity is None:
            continue
        baseline = baseline_activity * baseline_factor.factor_value
        actual = actual_activity * actual_factor.factor_value
        avoided = baseline - actual
        factors = [baseline_factor, actual_factor]
        method = f"baseline ({baseline_activity} x {baseline_factor.factor_value}) - actual ({actual_activity} x {actual_factor.factor_value})"
        produced.extend(
            [
                (baseline_key, baseline, method, factors, inputs),
                (actual_key, actual, method, factors, inputs),
                (avoided_key, avoided, method, factors, inputs),
            ]
        )
    fuel = methodology.parameters.get("fuel_avoided")
    if fuel:
        factor = _factor(db, fuel.get("factor_id"))
        activity = (
            _activity(action, fuel.get("basis", factor.unit_basis if factor else ""))
            if factor
            else None
        )
        if factor and activity is not None:
            produced.append(
                (
                    EnvironmentalMetricKey.FUEL_AVOIDED_L,
                    activity * factor.factor_value,
                    "Baseline fuel activity multiplied by documented factor",
                    [factor],
                    inputs,
                )
            )
    db.execute(
        delete(EnvironmentalActionMetric).where(EnvironmentalActionMetric.action_id == action.id)
    )
    for key, value, method, factors, metric_inputs in produced:
        db.add(
            EnvironmentalActionMetric(
                action_id=action.id,
                metric_key=key,
                unit=METRIC_UNITS[key],
                calculated_value=value,
                calculation_method=method,
                calculation_snapshot=_snapshot(action, methodology, factors, metric_inputs),
            )
        )
    action.status = (
        EnvironmentalActionStatus.CALCULATED if produced else EnvironmentalActionStatus.NEEDS_REVIEW
    )
    action.updated_at = _utcnow()
    db.commit()
    return get_action(db, event_id, action_id, user)


def override_metric(
    db: Session,
    event_id: UUID,
    action_id: UUID,
    metric_id: UUID,
    payload: MetricOverride,
    user: User,
) -> EnvironmentalActionMetric:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only administrators can override results")
    _manage(db, event_id, user)
    action = get_action(db, event_id, action_id, user)
    metric = db.scalar(
        select(EnvironmentalActionMetric).where(
            EnvironmentalActionMetric.id == metric_id,
            EnvironmentalActionMetric.action_id == action.id,
        )
    )
    if metric is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    _invalidate_review(db, action, user, "Resultado reemplazado manualmente")
    metric.reported_value = payload.reported_value
    metric.is_manual_override = True
    metric.override_reason = payload.override_reason
    metric.updated_at = _utcnow()
    db.commit()
    db.refresh(metric)
    return metric


def summary(
    db: Session, event_id: UUID, session_id: UUID | None, user: User
) -> EnvironmentalSummary:
    _view(db, event_id, user)
    _session(db, event_id, session_id)
    action_filter = [EnvironmentalAction.event_id == event_id]
    if user.role == UserRole.CLIENT:
        action_filter.append(
            EnvironmentalAction.review_status == EnvironmentalReviewStatus.APPROVED
        )
    if session_id is not None:
        action_filter.append(EnvironmentalAction.session_id == session_id)
    count = db.scalar(select(func.count(EnvironmentalAction.id)).where(*action_filter)) or 0
    rows = db.execute(
        select(
            EnvironmentalActionMetric.metric_key,
            func.sum(
                func.coalesce(
                    EnvironmentalActionMetric.reported_value,
                    EnvironmentalActionMetric.calculated_value,
                )
            ),
        )
        .join(EnvironmentalAction)
        .where(*action_filter)
        .group_by(EnvironmentalActionMetric.metric_key)
    ).all()
    values = {key: value for key, value in rows}
    equivalence_factors = db.scalars(
        select(EcoEquivalenceFactor)
        .where(EcoEquivalenceFactor.is_active.is_(True))
        .order_by(EcoEquivalenceFactor.name)
    ).all()
    equivalences = [
        {
            "id": item.id,
            "key": item.key,
            "name": item.name,
            "metric_source": item.metric_source,
            "source_value": values[item.metric_source],
            "factor": item.factor,
            "value": values[item.metric_source] * item.factor,
            "unit": item.unit,
            "source": item.source,
            "year": item.year,
        }
        for item in equivalence_factors
        if item.metric_source in values
    ]
    targets = [
        EnvironmentalMetricKey.ENERGY_KWH,
        EnvironmentalMetricKey.FUEL_AVOIDED_L,
        EnvironmentalMetricKey.CO2E_AVOIDED_KG,
        EnvironmentalMetricKey.PM25_AVOIDED_KG,
        EnvironmentalMetricKey.PM10_AVOIDED_KG,
        EnvironmentalMetricKey.NOX_AVOIDED_KG,
    ]
    return EnvironmentalSummary(
        event_id=event_id,
        session_id=session_id,
        actions_count=count,
        energy_kwh=values.get(targets[0]),
        fuel_avoided_l=values.get(targets[1]),
        co2e_avoided_kg=values.get(targets[2]),
        pm25_avoided_kg=values.get(targets[3]),
        pm10_avoided_kg=values.get(targets[4]),
        nox_avoided_kg=values.get(targets[5]),
        unavailable_metrics=[key for key in targets if key not in values],
        equivalences=equivalences,
    )


def _invalidate_review(db: Session, action: EnvironmentalAction, user: User, reason: str) -> None:
    if action.review_status == EnvironmentalReviewStatus.DRAFT:
        return
    db.add(
        EnvironmentalActionReview(
            action_id=action.id,
            revision=action.review_revision,
            decision=EnvironmentalReviewDecision.INVALIDATED,
            comment=reason,
            actor_id=user.id,
        )
    )
    action.review_revision += 1
    action.review_status = EnvironmentalReviewStatus.DRAFT
    action.submitted_at = None
    action.submitted_by = None
    action.reviewed_at = None
    action.reviewed_by = None
    action.review_comment = reason


def submit_review(db: Session, event_id: UUID, action_id: UUID, user: User) -> EnvironmentalAction:
    _manage(db, event_id, user)
    action = get_action(db, event_id, action_id, user)
    if action.status != EnvironmentalActionStatus.CALCULATED or not action.metrics:
        raise HTTPException(status_code=409, detail="The action must be calculated before review")
    if action.review_status == EnvironmentalReviewStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="The action is already under review")
    action.review_status = EnvironmentalReviewStatus.IN_REVIEW
    action.submitted_at = _utcnow()
    action.submitted_by = user.id
    action.reviewed_at = None
    action.reviewed_by = None
    action.review_comment = None
    db.add(
        EnvironmentalActionReview(
            action_id=action.id,
            revision=action.review_revision,
            decision=EnvironmentalReviewDecision.SUBMITTED,
            actor_id=user.id,
        )
    )
    db.commit()
    return get_action(db, event_id, action_id, user)


def review_action(
    db: Session,
    event_id: UUID,
    action_id: UUID,
    payload: EnvironmentalReviewRequest,
    user: User,
) -> EnvironmentalAction:
    if user.role not in {UserRole.SUPER_ADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only administrators can review results")
    _manage(db, event_id, user)
    action = get_action(db, event_id, action_id, user)
    if action.review_status != EnvironmentalReviewStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="The action is not under review")
    status_by_decision = {
        EnvironmentalReviewDecision.APPROVED: EnvironmentalReviewStatus.APPROVED,
        EnvironmentalReviewDecision.CHANGES_REQUESTED: EnvironmentalReviewStatus.CHANGES_REQUESTED,
        EnvironmentalReviewDecision.REJECTED: EnvironmentalReviewStatus.REJECTED,
    }
    action.review_status = status_by_decision[payload.decision]
    action.reviewed_at = _utcnow()
    action.reviewed_by = user.id
    action.review_comment = payload.comment
    db.add(
        EnvironmentalActionReview(
            action_id=action.id,
            revision=action.review_revision,
            decision=payload.decision,
            comment=payload.comment,
            actor_id=user.id,
        )
    )
    db.commit()
    return get_action(db, event_id, action_id, user)


def review_history(db: Session, event_id: UUID, action_id: UUID, user: User) -> list[dict]:
    action = get_action(db, event_id, action_id, user)
    rows = db.execute(
        select(EnvironmentalActionReview, User.full_name)
        .outerjoin(User, User.id == EnvironmentalActionReview.actor_id)
        .where(EnvironmentalActionReview.action_id == action.id)
        .order_by(EnvironmentalActionReview.created_at.desc())
    ).all()
    return [
        {
            "id": item.id,
            "revision": item.revision,
            "decision": item.decision,
            "comment": item.comment,
            "actor_id": item.actor_id,
            "actor_name": actor_name,
            "created_at": item.created_at,
        }
        for item, actor_name in rows
    ]


def official_data(db: Session, event_id: UUID, session_id: UUID | None = None) -> dict:
    """Build the immutable, approved-only dataset used by reports and client views."""
    filters = [
        EnvironmentalAction.event_id == event_id,
        EnvironmentalAction.review_status == EnvironmentalReviewStatus.APPROVED,
    ]
    if session_id is not None:
        filters.append(EnvironmentalAction.session_id == session_id)
    actions = list(
        db.scalars(
            select(EnvironmentalAction)
            .options(
                selectinload(EnvironmentalAction.metrics),
                selectinload(EnvironmentalAction.methodology),
            )
            .where(*filters)
            .order_by(EnvironmentalAction.updated_at)
        )
        .unique()
        .all()
    )
    session_ids = {action.session_id for action in actions if action.session_id}
    session_names = (
        dict(
            db.execute(
                select(EventSession.id, EventSession.name).where(EventSession.id.in_(session_ids))
            ).all()
        )
        if session_ids
        else {}
    )
    reviewer_ids = {action.reviewed_by for action in actions if action.reviewed_by}
    reviewer_names = (
        dict(db.execute(select(User.id, User.full_name).where(User.id.in_(reviewer_ids))).all())
        if reviewer_ids
        else {}
    )
    metric_keys = [
        EnvironmentalMetricKey.ENERGY_KWH,
        EnvironmentalMetricKey.FUEL_AVOIDED_L,
        EnvironmentalMetricKey.CO2E_BASELINE_KG,
        EnvironmentalMetricKey.CO2E_ACTUAL_KG,
        EnvironmentalMetricKey.CO2E_AVOIDED_KG,
        EnvironmentalMetricKey.PM25_AVOIDED_KG,
        EnvironmentalMetricKey.PM10_AVOIDED_KG,
        EnvironmentalMetricKey.NOX_AVOIDED_KG,
    ]
    totals = {key.value: ZERO for key in metric_keys}
    present: set[str] = set()
    breakdown: dict[str, dict] = {}
    methodologies: dict[str, dict] = {}
    sources: dict[str, dict] = {}
    action_rows = []
    for action in actions:
        values = {}
        for metric in action.metrics:
            if metric.metric_key not in metric_keys or metric.value is None:
                continue
            key = metric.metric_key.value
            totals[key] += metric.value
            present.add(key)
            values[key] = str(metric.value)
            snapshot = metric.calculation_snapshot or {}
            method = snapshot.get("methodology") or {}
            if method.get("id"):
                methodologies[method["id"]] = method
            for factor in snapshot.get("factors") or []:
                if factor.get("id"):
                    sources[factor["id"]] = factor
        scope_key = str(action.session_id) if action.session_id else "EVENT"
        scope = breakdown.setdefault(
            scope_key,
            {
                "session_id": str(action.session_id) if action.session_id else None,
                "session_name": session_names.get(action.session_id, "Evento completo"),
                "actions_count": 0,
                "metrics": {key.value: ZERO for key in metric_keys},
            },
        )
        scope["actions_count"] += 1
        for key, value in values.items():
            scope["metrics"][key] += Decimal(value)
        action_rows.append(
            {
                "id": str(action.id),
                "name": action.name,
                "action_type": action.action_type.value,
                "session_id": str(action.session_id) if action.session_id else None,
                "session_name": session_names.get(action.session_id, "Evento completo"),
                "methodology": action.methodology.name if action.methodology else None,
                "metrics": values,
                "review_revision": action.review_revision,
                "approved_at": action.reviewed_at.isoformat() if action.reviewed_at else None,
                "approved_by": reviewer_names.get(action.reviewed_by),
            }
        )
    equivalence_factors = db.scalars(
        select(EcoEquivalenceFactor).where(EcoEquivalenceFactor.is_active.is_(True))
    ).all()
    equivalences = [
        {
            "name": item.name,
            "value": str(totals[item.metric_source.value] * item.factor),
            # Catalog units describe the conversion factor (for example,
            # L/kgCO2e). The calculated result is expressed only in its
            # numerator unit.
            "unit": item.unit.split("/", 1)[0],
            "source": item.source,
            "year": item.year,
        }
        for item in equivalence_factors
        if item.metric_source.value in present
    ]
    return {
        "event_id": str(event_id),
        "session_id": str(session_id) if session_id else None,
        "actions_count": len(actions),
        "metrics": {key: str(value) if key in present else None for key, value in totals.items()},
        "actions": action_rows,
        "breakdown": [
            {
                **scope,
                "metrics": {
                    key: str(value) if value != ZERO else "0"
                    for key, value in scope["metrics"].items()
                },
            }
            for scope in breakdown.values()
        ],
        "methodologies": list(methodologies.values()),
        "sources": list(sources.values()),
        "equivalences": equivalences,
        "disclaimer": "Resultados operacionales aprobados. Las equivalencias son referencias comunicacionales y no representan compensaciones ni certificaciones.",
    }
