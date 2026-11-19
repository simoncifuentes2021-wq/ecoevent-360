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
    executive_fields = [
        _field(
            "attendees",
            "Asistencia",
            (session.real_attendees or session.expected_attendees) if show else (event.real_attendees or event.estimated_attendees),
            "SHOW" if show else "EVENT",
            "personas",
        ),
        _field(
            "shows",
            "Shows incluidos",
            1 if show else len(event.sessions),
            "SHOW" if show else "EVENT",
            "shows",
        ),
        _field(
            "duration_days",
            "Duración",
            max(1, (event.end_date.date() - event.start_date.date()).days + 1),
            "EVENT",
            "días",
        ),
    ]
    executive_narrative = (
        f"Este reporte consolida los principales resultados de "
        f"{session.name if show else event.name}."
    )
    result["executive_summary"] = _section(
        executive_fields,
        [
            {
                "summary": executive_narrative
            }
        ],
    )
    result["executive_summary"][0]["text"] = executive_narrative
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
        _field(
            "energy_kwh",
            "Energía generada",
            metrics["ENERGY_KWH"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kWh",
        ),
        _field(
            "fuel_avoided_l",
            "Diésel evitado",
            metrics["FUEL_AVOIDED_L"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "L",
        ),
        _field(
            "co2e_baseline_kg",
            "CO₂e línea base",
            metrics["CO2E_BASELINE_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
        _field(
            "co2e_actual_kg",
            "CO₂e escenario real",
            metrics["CO2E_ACTUAL_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
        _field(
            "co2e_avoided_kg",
            "CO₂e evitado",
            metrics["CO2E_AVOIDED_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
        _field(
            "pm25_avoided_kg",
            "PM2.5 evitado",
            metrics["PM25_AVOIDED_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
        _field(
            "pm10_avoided_kg",
            "PM10 evitado",
            metrics["PM10_AVOIDED_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
        _field(
            "nox_avoided_kg",
            "NOx evitado",
            metrics["NOX_AVOIDED_KG"],
            "APPROVED_ENVIRONMENTAL_ACTIONS",
            "kg",
        ),
    ]
    environmental_items = [
        {
            "_source_key": f"action:{action['id']}",
            "kind": "ACTION",
            "label": action["name"],
            "value": action["metrics"].get("CO2E_AVOIDED_KG"),
            "unit": "kg CO₂e evitado",
            "description": f"{action['session_name']} · {action['methodology'] or 'Metodología no informada'} · aprobado por {action['approved_by'] or 'usuario no disponible'}",
        }
        for action in official["actions"]
    ] + [
        {
            "_source_key": f"equivalence:{equivalence.get('key') or equivalence.get('id') or index}",
            "kind": "EQUIVALENCE",
            "label": equivalence["name"],
            "value": equivalence["value"],
            "unit": equivalence["unit"],
            "description": f"Referencia: {equivalence['source']} · {equivalence['year']}",
        }
        for index, equivalence in enumerate(official["equivalences"])
    ] + [
        {
            "_source_key": f"methodology:{methodology.get('id') or methodology.get('name') or index}",
            "kind": "METHODOLOGY",
            "label": methodology.get("name") or methodology.get("title") or "Metodología",
            "value": None,
            "unit": None,
            "description": methodology.get("description") or "Metodología aplicada a una acción aprobada.",
        }
        for index, methodology in enumerate(official.get("methodologies") or [])
    ] + [
        {
            "_source_key": f"source:{source.get('id') or source.get('technology') or index}",
            "kind": "SOURCE",
            "label": source.get("technology") or "Factor ambiental",
            "value": source.get("year"),
            "unit": "Año",
            "description": source.get("source") or "Fuente documentada",
        }
        for index, source in enumerate(official.get("sources") or [])
    ]
    environmental = _section(
        environmental_fields,
        environmental_items,
        availability="AVAILABLE" if official["actions_count"] else "NO_DATA",
        source_scope="APPROVED_SHOW" if show else "APPROVED_EVENT",
    )
    environmental[0]["text"] = official["disclaimer"]
    environmental[0]["text_origin"] = "AUTOFILLED"
    environmental[0]["traceability_title"] = "Trazabilidad aprobada"
    environmental[0]["traceability_summary"] = (
        f"{official['actions_count']} acciones aprobadas. "
        "Solo estos resultados forman parte del reporte oficial."
    )
    environmental[1]["text"] = official["disclaimer"]
    environmental[1]["text_origin"] = "AUTOFILLED"
    environmental[1]["traceability_title"] = "Trazabilidad aprobada"
    environmental[1]["traceability_summary"] = (
        f"{official['actions_count']} acciones aprobadas. "
        "Solo estos resultados forman parte del reporte oficial."
    )
    environmental[1]["official_data"] = official
    environmental[2]["approved_actions_count"] = official["actions_count"]
    result["environmental_impact"] = environmental
    result["evidences"] = _section([], [], availability="NO_DATA")
    for key in ("operations", "recommendations", "conclusion"):
        result[key] = _section([], [], availability="NO_DATA")
    return result


def merge_preserving_overrides(
    old: dict, fresh: dict, old_source_snapshot: dict | None = None
) -> dict:
    old_source_snapshot = old_source_snapshot or {}
    old_fields = {field.get("key"): field for field in old.get("fields", [])}
    snapshot_fields = {
        field.get("key"): field for field in old_source_snapshot.get("fields", [])
    }
    for field in fresh.get("fields", []):
        previous = old_fields.get(field["key"])
        if previous:
            field["is_visible"] = previous.get("is_visible", True)
            previous_auto = snapshot_fields.get(field["key"], {})
            label_was_edited = previous.get("label_overridden") or (
                previous.get("label") != previous_auto.get("label")
            )
            if label_was_edited:
                field["label"] = previous.get("label")
                field["label_overridden"] = True
            description_was_edited = previous.get("description_overridden") or (
                previous.get("description") != previous_auto.get("description")
            )
            if description_was_edited:
                field["description"] = previous.get("description")
                field["description_overridden"] = True
            if previous.get("unit") != previous_auto.get("unit"):
                field["unit"] = previous.get("unit")
        if previous and previous.get("is_overridden"):
            field["value"] = previous.get("value")
            field["is_overridden"] = True
    if "text" in old:
        text_was_edited = old.get("text_origin") in {"MANUAL", "GENERATED", "ENRICHED"} or (
            old.get("text") != old_source_snapshot.get("text")
        )
        if text_was_edited:
            fresh["text"] = old.get("text")
            fresh["text_origin"] = old.get("text_origin") or "MANUAL"
            fresh["ai_generation_id"] = old.get("ai_generation_id")
    if "show_traceability" in old:
        fresh["show_traceability"] = old["show_traceability"]
    if "show_scope_results" in old:
        fresh["show_scope_results"] = old["show_scope_results"]
    for key in ("traceability_title", "traceability_summary", "scope_results_title"):
        if key in old and old.get(key) != old_source_snapshot.get(key):
            fresh[key] = old.get(key)

    old_items = old.get("items", [])
    snapshot_items = old_source_snapshot.get("items", [])
    old_by_source_key = {
        item.get("_source_key"): item for item in old_items if item.get("_source_key")
    }
    old_by_label = {item.get("label"): item for item in old_items if item.get("label")}
    snapshot_by_source_key = {
        item.get("_source_key"): item for item in snapshot_items if item.get("_source_key")
    }
    snapshot_by_label = {
        item.get("label"): item for item in snapshot_items if item.get("label")
    }
    old_source_keys = {
        item.get("_source_key") for item in old_items if item.get("_source_key")
    }
    snapshot_source_keys = {
        item.get("_source_key") for item in snapshot_items if item.get("_source_key")
    }
    removed_source_keys = snapshot_source_keys - old_source_keys
    old_labels = {item.get("label") for item in old_items if item.get("label")}
    snapshot_labels = {item.get("label") for item in snapshot_items if item.get("label")}
    removed_legacy_labels = snapshot_labels - old_labels
    merged_items = []
    for item in fresh.get("items", []):
        source_key = item.get("_source_key")
        if source_key in removed_source_keys or (
            not source_key and item.get("label") in removed_legacy_labels
        ):
            continue
        previous = old_by_source_key.get(source_key) if source_key else None
        if previous is None:
            previous = old_by_label.get(item.get("label"))
        if previous:
            item["_is_visible"] = previous.get("_is_visible", True)
            previous_snapshot = (
                snapshot_by_source_key.get(previous.get("_source_key"))
                if previous.get("_source_key")
                else snapshot_by_label.get(previous.get("label"), {})
            ) or {}
            for key, flag in (
                ("label", "_label_overridden"),
                ("value", "_value_overridden"),
                ("unit", "_unit_overridden"),
                ("description", "_description_overridden"),
                ("kind", "_kind_overridden"),
            ):
                if previous.get(flag) or previous.get(key) != previous_snapshot.get(key):
                    item[key] = previous.get(key)
                    item[flag] = True
        merged_items.append(item)
    fresh["items"] = merged_items
    fresh["items"].extend(item for item in old_items if item.get("_manual") is True)
    return fresh
