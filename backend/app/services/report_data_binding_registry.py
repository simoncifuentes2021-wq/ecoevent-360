from dataclasses import dataclass
from typing import Any, Callable

from app.models.core import Report


@dataclass(frozen=True)
class BindingDefinition:
    key: str
    label: str
    unit: str | None
    source: str
    resolver: Callable[[Report], Any]


def _field(section_key: str, field_key: str) -> Callable[[Report], Any]:
    def resolve(report: Report) -> Any:
        section = next((item for item in report.sections if item.section_key == section_key), None)
        if not section:
            return None
        field = next(
            (
                item
                for item in (section.content or {}).get("fields", [])
                if item.get("key") == field_key
            ),
            None,
        )
        return field.get("value") if field else None

    return resolve


REGISTRY = {
    item.key: item
    for item in (
        BindingDefinition("event.name", "Nombre del evento", None, "event", lambda r: r.event.name),
        BindingDefinition(
            "event.client", "Cliente", None, "event", lambda r: r.event.client.business_name
        ),
        BindingDefinition(
            "event.start_date",
            "Inicio del evento",
            None,
            "event",
            lambda r: r.event.start_date.isoformat(),
        ),
        BindingDefinition(
            "event.end_date",
            "Fin del evento",
            None,
            "event",
            lambda r: r.event.end_date.isoformat(),
        ),
        BindingDefinition(
            "event.real_attendees",
            "Asistentes reales",
            "personas",
            "event_info",
            _field("event_info", "real_attendees"),
        ),
        BindingDefinition(
            "show.name",
            "Nombre del show",
            None,
            "show",
            lambda r: r.session.name if r.session else None,
        ),
        BindingDefinition(
            "show.real_attendees",
            "Asistentes reales del show",
            "personas",
            "show_info",
            _field("show_info", "real_attendees"),
        ),
        BindingDefinition(
            "bike_zone.users",
            "Usuarios Bike Zone",
            "personas",
            "bike_zone",
            _field("bike_zone", "users"),
        ),
        BindingDefinition(
            "waste.total_kg", "Residuos totales", "kg", "waste", _field("waste", "total_kg")
        ),
        BindingDefinition(
            "carbon.total_kgco2e",
            "Huella de carbono",
            "kgCO2e",
            "carbon",
            _field("carbon", "total_kgco2e"),
        ),
        BindingDefinition(
            "environmental_impact.co2e_avoided_kg",
            "CO2e evitado",
            "kgCO2e",
            "environmental_impact",
            _field("environmental_impact", "co2e_avoided_kg"),
        ),
        BindingDefinition("tasks.total", "Tareas", None, "tasks", _field("tasks", "total")),
        BindingDefinition(
            "tasks.completion_rate",
            "Cumplimiento de tareas",
            "%",
            "tasks",
            _field("tasks", "completion_rate"),
        ),
        BindingDefinition(
            "incidents.total", "Incidentes", None, "incidents", _field("incidents", "total")
        ),
        BindingDefinition(
            "forms.responses",
            "Respuestas de formularios",
            None,
            "forms",
            _field("forms", "responses"),
        ),
    )
}


def canonical_key(binding: dict | None) -> str | None:
    if not binding:
        return None
    key = binding.get("key") or (
        f"{binding.get('source')}.{binding.get('metric')}"
        if binding.get("source") and binding.get("metric")
        else None
    )
    if key not in REGISTRY:
        raise ValueError("Unknown report data binding")
    return key


def resolve(report: Report, binding: dict | None) -> dict | None:
    key = canonical_key(binding)
    if not key:
        return None
    definition = REGISTRY[key]
    value = definition.resolver(report)
    return {
        "key": key,
        "label": definition.label,
        "value": value,
        "unit": definition.unit,
        "source": definition.source,
        "availability": "AVAILABLE" if value is not None else "NO_DATA",
    }


def catalog(report: Report) -> list[dict]:
    return [resolve(report, {"key": key}) for key in REGISTRY]
