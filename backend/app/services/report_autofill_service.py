from collections import Counter
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    BikeZoneRecord,
    CarbonRecord,
    Event,
    EventService,
    EventSession,
    EventSessionStaff,
    EventStaff,
    FormResponse,
    Incident,
    Service,
    Task,
    WasteRecord,
    WasteType,
)
from app.models.enums import IncidentStatus, TaskStatus
from app.services.environmental_calculation_service import official_data


def _scalar(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _field(key, label, value, source, unit=None):
    return {
        "key": key,
        "label": label,
        "auto_value": _scalar(value),
        "value": _scalar(value),
        "unit": unit,
        "description": None,
        "is_overridden": False,
        "source": source,
    }


def _section(fields=None, items=None, *, availability="AVAILABLE", source_scope="SHOW_SCOPED"):
    fields, items = fields or [], items or []
    if not fields and not items and availability == "AVAILABLE":
        availability = "NO_DATA"
    content = {"text": None, "fields": fields, "items": items}
    return (
        content,
        content,
        {
            "availability": availability,
            "source_scope": source_scope,
            "generated_at": datetime.utcnow().isoformat(),
        },
    )


def build_sections(
    db: Session, event: Event, session: EventSession | None
) -> dict[str, tuple[dict, dict, dict]]:
    show = session is not None
    result = {}
    cover = [
        _field(
            "title",
            "Título",
            f"Reporte {'del show ' + session.name if show else 'del evento ' + event.name}",
            "EVENT",
        ),
        _field("client", "Cliente", event.client.business_name, "EVENT"),
        _field("event", "Evento", event.name, "EVENT"),
        _field(
            "date",
            "Fecha",
            session.session_date if show else event.start_date.date(),
            "SHOW" if show else "EVENT",
        ),
        _field(
            "venue",
            "Recinto",
            session.venue_name if show else event.location_name,
            "SHOW" if show else "EVENT",
        ),
    ]
    result["cover"] = _section(cover)
    result["executive_summary"] = _section(
        [],
        [
            {
                "summary": f"Este reporte consolida los principales resultados de {session.name if show else event.name}."
            }
        ],
    )
    result["event_info"] = _section(
        [
            _field("name", "Nombre", event.name, "EVENT"),
            _field("type", "Tipo", event.event_type, "EVENT"),
            _field("location", "Ubicación", event.location_name, "EVENT"),
            _field("city", "Ciudad", event.city, "EVENT"),
            _field("region", "Región", event.region, "EVENT"),
            _field("start_date", "Inicio", event.start_date, "EVENT"),
            _field("end_date", "Término", event.end_date, "EVENT"),
            _field(
                "estimated_attendees", "Asistencia estimada", event.estimated_attendees, "EVENT"
            ),
            _field("real_attendees", "Asistencia real", event.real_attendees, "EVENT"),
        ],
        source_scope="EVENT_LEVEL",
    )
    if show:
        result["show_info"] = _section(
            [
                _field("name", "Show", session.name, "SHOW"),
                _field("date", "Fecha", session.session_date, "SHOW"),
                _field("start_time", "Inicio", session.start_time, "SHOW"),
                _field("end_time", "Término", session.end_time, "SHOW"),
                _field("venue", "Recinto", session.venue_name, "SHOW"),
                _field("stage", "Escenario", session.stage_name, "SHOW"),
                _field(
                    "expected_attendees", "Asistencia estimada", session.expected_attendees, "SHOW"
                ),
                _field("real_attendees", "Asistencia real", session.real_attendees, "SHOW"),
                _field("status", "Estado", session.status, "SHOW"),
            ]
        )
    services = db.execute(
        select(Service.name, EventService.quantity)
        .join(EventService, EventService.service_id == Service.id)
        .where(EventService.event_id == event.id)
    ).all()
    result["services"] = _section(
        items=[{"name": n, "quantity": _scalar(q)} for n, q in services], source_scope="EVENT_LEVEL"
    )
    if show:
        staff_rows = db.scalars(
            select(EventSessionStaff).where(EventSessionStaff.session_id == session.id)
        ).all()
        roles = Counter(x.operational_role or "Sin rol" for x in staff_rows)
    else:
        staff_rows = db.scalars(select(EventStaff).where(EventStaff.event_id == event.id)).all()
        roles = Counter(x.role_in_event or "Sin rol" for x in staff_rows)
    result["staff"] = _section(
        [_field("total", "Personas", len(staff_rows), "STAFF")],
        [{"role": k, "count": v} for k, v in roles.items()],
    )
    for key, model, statuses in (
        ("tasks", Task, TaskStatus),
        ("incidents", Incident, IncidentStatus),
    ):
        query = select(model.status, func.count()).where(model.event_id == event.id)
        if show:
            query = query.where(model.session_id == session.id)
        counts = {str(s.value): c for s, c in db.execute(query.group_by(model.status)).all()}
        fields = [_field("total", "Total", sum(counts.values()), key.upper())] + [
            _field(k.lower(), k.replace("_", " ").title(), v, key.upper())
            for k, v in counts.items()
        ]
        if key == "tasks":
            total = sum(counts.values())
            fields.append(
                _field(
                    "completion_rate",
                    "Cumplimiento",
                    round(100 * counts.get("COMPLETED", 0) / total, 1) if total else 0,
                    "TASKS",
                    "%",
                )
            )
        result[key] = _section(fields)
    response_query = (
        select(func.count()).select_from(FormResponse).where(FormResponse.event_id == event.id)
    )
    bike_query = select(BikeZoneRecord.status, func.count()).where(
        BikeZoneRecord.event_id == event.id
    )
    if show:
        response_query = response_query.where(FormResponse.session_id == session.id)
        bike_query = bike_query.where(BikeZoneRecord.session_id == session.id)
    result["forms"] = _section(
        [_field("responses", "Respuestas", db.scalar(response_query) or 0, "FORMS")]
    )
    bikes = {s.value: c for s, c in db.execute(bike_query.group_by(BikeZoneRecord.status)).all()}
    result["bike_zone"] = _section(
        [_field("users", "Usuarios registrados", sum(bikes.values()), "BIKE_ZONE")]
        + [_field(k.lower(), k.title(), v, "BIKE_ZONE") for k, v in bikes.items()]
    )
    for key, model, column, label, unit in (
        ("waste", WasteRecord, WasteRecord.weight_kg, "Residuos totales", "kg"),
        ("carbon", CarbonRecord, CarbonRecord.emissions_kgco2e, "Emisiones totales", "kgCO2e"),
    ):
        value = db.scalar(
            select(func.coalesce(func.sum(column), 0)).where(model.event_id == event.id)
        )
        if key == "waste":
            grouped = db.execute(
                select(WasteType.name, func.sum(WasteRecord.weight_kg))
                .join(WasteType, WasteType.id == WasteRecord.waste_type_id, isouter=True)
                .where(WasteRecord.event_id == event.id)
                .group_by(WasteType.name)
                .order_by(func.sum(WasteRecord.weight_kg).desc())
            ).all()
            items = [
                {"label": name or "Sin tipo", "value": _scalar(total), "unit": "kg"}
                for name, total in grouped
            ]
        else:
            grouped = db.execute(
                select(CarbonRecord.category, func.sum(CarbonRecord.emissions_kgco2e))
                .where(CarbonRecord.event_id == event.id)
                .group_by(CarbonRecord.category)
                .order_by(func.sum(CarbonRecord.emissions_kgco2e).desc())
            ).all()
            items = [
                {"label": category, "value": _scalar(total), "unit": "kgCO2e"}
                for category, total in grouped
            ]
        availability = "EVENT_LEVEL_ONLY" if show else "AVAILABLE"
        result[key] = _section(
            [_field("total", label, value, key.upper(), unit)],
            items,
            availability=availability,
            source_scope="EVENT_LEVEL",
        )
    official = official_data(db, event.id, session.id if session else None)
    metrics = official["metrics"]
    environmental_fields = [
        _field("energy_kwh", "Energía utilizada", metrics["ENERGY_KWH"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kWh"),
        _field("fuel_avoided_l", "Combustible evitado", metrics["FUEL_AVOIDED_L"], "APPROVED_ENVIRONMENTAL_ACTIONS", "L"),
        _field("co2e_baseline_kg", "CO₂e línea base", metrics["CO2E_BASELINE_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
        _field("co2e_actual_kg", "CO₂e escenario real", metrics["CO2E_ACTUAL_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
        _field("co2e_avoided_kg", "CO₂e evitado", metrics["CO2E_AVOIDED_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
        _field("pm25_avoided_kg", "PM2.5 evitado", metrics["PM25_AVOIDED_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
        _field("pm10_avoided_kg", "PM10 evitado", metrics["PM10_AVOIDED_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
        _field("nox_avoided_kg", "NOx evitado", metrics["NOX_AVOIDED_KG"], "APPROVED_ENVIRONMENTAL_ACTIONS", "kg"),
    ]
    environmental_items = [
        {
            "label": action["name"],
            "value": action["metrics"].get("CO2E_AVOIDED_KG"),
            "unit": "kg CO₂e evitado",
            "description": f"{action['session_name']} · {action['methodology'] or 'Metodología no informada'} · aprobado por {action['approved_by'] or 'usuario no disponible'}",
        }
        for action in official["actions"]
    ] + [
        {
            "label": equivalence["name"],
            "value": equivalence["value"],
            "unit": equivalence["unit"],
            "description": f"Referencia: {equivalence['source']} · {equivalence['year']}",
        }
        for equivalence in official["equivalences"]
    ]
    environmental = _section(
        environmental_fields,
        environmental_items,
        availability="AVAILABLE" if official["actions_count"] else "NO_DATA",
        source_scope="APPROVED_SHOW" if show else "APPROVED_EVENT",
    )
    environmental[0]["text"] = official["disclaimer"]
    environmental[1]["text"] = official["disclaimer"]
    environmental[1]["official_data"] = official
    environmental[2]["approved_actions_count"] = official["actions_count"]
    result["environmental_impact"] = environmental
    result["evidences"] = _section([], [], availability="NO_DATA")
    for key in ("operations", "recommendations", "conclusion"):
        result[key] = _section([], [], availability="NO_DATA")
    return result


def merge_preserving_overrides(old: dict, fresh: dict) -> dict:
    old_fields = {field.get("key"): field for field in old.get("fields", [])}
    for field in fresh.get("fields", []):
        previous = old_fields.get(field["key"])
        if previous:
            field["is_visible"] = previous.get("is_visible", True)
            field["description"] = previous.get("description")
        if previous and previous.get("is_overridden"):
            field["value"] = previous.get("value")
            field["is_overridden"] = True
    if old.get("text") is not None:
        fresh["text"] = old["text"]
    old_items = old.get("items", [])
    old_by_label = {item.get("label"): item for item in old_items if item.get("label")}
    for item in fresh.get("items", []):
        previous = old_by_label.get(item.get("label"))
        if previous:
            item["_is_visible"] = previous.get("_is_visible", True)
            item["description"] = previous.get("description")
    fresh["items"].extend(item for item in old_items if item.get("_manual") is True)
    return fresh
