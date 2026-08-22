from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Event, EventSession, User
from app.models.environmental import EcoEquivalenceFactor, EnvironmentalAction
from app.services import environmental_calculation_service

CAPABILITY = "environmental.interpretation"


def _decimal(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def build_environmental_context(
    db: Session, event_id: UUID, action_id: UUID, user: User
) -> tuple[EnvironmentalAction, dict]:
    action = environmental_calculation_service.get_action(db, event_id, action_id, user)
    event = db.get(Event, event_id)
    session = db.get(EventSession, action.session_id) if action.session_id else None
    values = {metric.metric_key.value: metric.value for metric in action.metrics}
    methodology = action.methodology

    controlled_equivalences = []
    factors = db.scalars(
        select(EcoEquivalenceFactor).where(EcoEquivalenceFactor.is_active.is_(True))
    ).all()
    for factor in factors:
        source_value = values.get(factor.metric_source.value)
        if source_value is None:
            continue
        controlled_equivalences.append(
            {
                "name": factor.name,
                "value": _decimal(source_value * factor.factor),
                "unit": factor.unit,
                "source": factor.source,
                "factor_version": str(factor.year),
            }
        )

    context = {
        "scope": {
            "event": event.name if event else None,
            "show": session.name if session else None,
        },
        "action": {
            "type": action.action_type.value,
            "name": action.name,
            "quantity_used": _decimal(action.quantity_used),
            "hours_used": _decimal(action.hours_used),
            "energy_input_mode": action.energy_input_mode.value,
            "energy_per_unit_hour_kwh": _decimal(action.energy_per_unit_hour_kwh),
        },
        "certified_results": {
            "energy_generated_kwh": _decimal(values.get("ENERGY_KWH") or action.energy_kwh),
            "diesel_avoided_l": _decimal(values.get("FUEL_AVOIDED_L")),
            "co2e_avoided_kg": _decimal(values.get("CO2E_AVOIDED_KG")),
            "pm25_avoided_kg": _decimal(values.get("PM25_AVOIDED_KG")),
            "pm10_avoided_kg": _decimal(values.get("PM10_AVOIDED_KG")),
            "nox_avoided_kg": _decimal(values.get("NOX_AVOIDED_KG")),
        },
        "methodology": {
            "name": methodology.name if methodology else None,
            "baseline_technology": methodology.baseline_technology if methodology else None,
            "actual_technology": methodology.actual_technology if methodology else None,
        },
        "controlled_equivalences": controlled_equivalences,
    }
    return action, context
