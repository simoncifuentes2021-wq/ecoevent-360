"""Controlled, deterministic visual enrichment for the professional renderer."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

PRESETS = {
    "ECOEVENT_EDITORIAL": {"label": "EcoEvent editorial", "tone": "editorial"},
    "EXECUTIVE": {"label": "Ejecutivo", "tone": "executive"},
    "ENVIRONMENTAL": {"label": "Ambiental", "tone": "environmental"},
    "BIKE_ZONE": {"label": "Bike Zone", "tone": "bike"},
    "IMPACT": {"label": "Impacto", "tone": "impact"},
}

PRESET_SECTION_VARIANTS = {
    "ECOEVENT_EDITORIAL": {
        "EVENT_INFO": "EVENT_INFO_EDITORIAL", "BIKE_ZONE": "BIKE_ZONE_MOBILITY",
        "WASTE": "WASTE_CIRCULARITY", "CARBON": "CARBON_FOOTPRINT",
        "ENVIRONMENTAL_IMPACT": "ENVIRONMENTAL_IMPACT_STORY",
    },
    "EXECUTIVE": {
        "EVENT_INFO": "EVENT_INFO_EDITORIAL", "BIKE_ZONE": "BIKE_ZONE_MOBILITY",
        "WASTE": "WASTE_CIRCULARITY", "CARBON": "CARBON_FOOTPRINT",
        "ENVIRONMENTAL_IMPACT": "ENVIRONMENTAL_IMPACT_STORY",
    },
    "ENVIRONMENTAL": {
        "EVENT_INFO": "EVENT_INFO_EDITORIAL", "BIKE_ZONE": "BIKE_ZONE_MOBILITY",
        "WASTE": "WASTE_CIRCULARITY", "CARBON": "CARBON_FOOTPRINT",
        "ENVIRONMENTAL_IMPACT": "ENVIRONMENTAL_IMPACT_STORY",
    },
    "BIKE_ZONE": {"BIKE_ZONE": "BIKE_ZONE_MOBILITY"},
    "IMPACT": {
        "WASTE": "WASTE_CIRCULARITY", "CARBON": "CARBON_FOOTPRINT",
        "ENVIRONMENTAL_IMPACT": "ENVIRONMENTAL_IMPACT_STORY",
    },
}

SECTION_ICONS = {
    "EXECUTIVE_SUMMARY": "CHART", "EVENT_INFO": "CALENDAR", "SHOW_INFO": "LOCATION",
    "BIKE_ZONE": "BICYCLE", "WASTE": "RECYCLE", "CARBON": "CARBON",
    "ENVIRONMENTAL_IMPACT": "LEAF", "EVIDENCES": "CAMERA",
    "TASKS": "CHECK", "INCIDENTS": "ALERT", "FORMS": "CHART",
    "RECOMMENDATIONS": "LIGHTBULB", "CONCLUSION": "TARGET",
}

# Internal SVG allowlist. User input can select a key, never markup or a path.
ICON_PATHS = {
    "LEAF": "M19 3C10 3 5 8 5 15c0 3 2 5 5 5 7 0 9-9 9-17ZM5 21c2-6 6-10 12-13",
    "RECYCLE": "m7 19-3-5 3-5M4 14h7m6-9 3 5-3 5m3-5h-7M8 6l4-3 4 3m-4-3v7",
    "BICYCLE": "M5 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm14 0a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM5 13h5l3-6h3m-6 6 4 4 5-4M9 7h3",
    "CARBON": "M12 3a9 9 0 1 0 9 9M8 15c-3-5 1-9 6-7-1 5-3 8-6 7Z",
    "ENERGY": "m13 2-8 12h7l-1 8 8-12h-7l1-8Z", "WATER": "M12 2S6 9 6 14a6 6 0 0 0 12 0c0-5-6-12-6-12Z",
    "PEOPLE": "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8m13 18v-2a4 4 0 0 0-3-4",
    "LOCATION": "M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Zm-8 2a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
    "CALENDAR": "M3 5h18v16H3V5Zm4-3v6m10-6v6M3 10h18", "CHART": "M4 20V10m6 10V4m6 16v-7m5 7H2",
    "CHECK": "m4 12 5 5L20 6", "ALERT": "M12 3 2 21h20L12 3Zm0 6v5m0 3h.01", "LIGHTBULB": "M9 18h6m-5 4h4m3-8c1-1 2-3 2-5a7 7 0 1 0-14 0c0 2 1 4 2 5 1 1 2 2 2 4h6c0-2 1-3 2-4Z",
    "CAMERA": "M3 7h4l2-3h6l2 3h4v13H3V7Zm9 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "TARGET": "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-5a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-5 8-8",
}


def normalized(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = {"preset": "AUTO", "icon_density": "MEDIUM", "visual_density": "BALANCED", "show_icons": True, "show_trends": True, "show_equivalences": True}
    return {**base, **(raw or {})}


def icon_svg(key: str) -> str:
    path = ICON_PATHS.get(key, ICON_PATHS["LEAF"])
    return f'<svg aria-hidden="true" viewBox="0 0 24 24"><path d="{path}"/></svg>'


def section_variant(preset: str, section_type: str) -> str | None:
    return PRESET_SECTION_VARIANTS.get(preset, {}).get(section_type)


def format_metric(value: Any, unit: str | None = None, *, precision: int | None = None) -> str:
    """Human report formatting only; the stored numeric value is never changed."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    absolute = abs(number)
    digits = precision if precision is not None else (
        5 if absolute and absolute < Decimal("0.001") else 2 if number != number.to_integral() else 0
    )
    rendered = f"{number:.{digits}f}".rstrip("0").rstrip(".") if digits else f"{number:.0f}"
    if rendered in {"-0", ""}:
        rendered = "0"
    return rendered.replace(".", ",")


def normalize_unit(unit: str | None) -> str:
    return {"kgCO2e": "kg CO₂e", "tCO2e": "t CO₂e", "attendees": "asistentes"}.get(
        str(unit or ""), str(unit or "")
    )


def section_enrichment(section: dict[str, Any], visual: dict[str, Any], override: dict[str, Any] | None, editable_attr) -> str:
    override = override or {}
    preset = str(visual.get("preset") or "AUTO")
    variant = str(override.get("variant") or "AUTO")
    if preset == "AUTO" and variant == "AUTO":
        return ""
    key = str(section.get("section_key") or "section")
    content = section.get("content") or {}
    fields = [f for f in content.get("fields") or [] if f.get("is_visible", True) is not False]
    items = [i for i in content.get("items") or [] if i.get("_is_visible", True) is not False]
    icon_key = str(override.get("icon_key") or SECTION_ICONS.get(section.get("section_type"), "LEAF"))
    icon = icon_svg(icon_key) if visual.get("show_icons", True) and override.get("show_icon", True) else ""
    lead = fields[0] if fields else None
    metric = ""
    if lead:
        metric = f'<strong>{escape(str(lead.get("value") if lead.get("value") is not None else "—"))}<small>{escape(str(lead.get("unit") or ""))}</small></strong><span>{escape(str(lead.get("label") or "Indicador clave"))}</span>'
    chips = "".join(f'<span>{escape(str(item.get("label") or item.get("name") or "Resultado"))}</span>' for item in items[:4])
    return f'<aside class="premium-insight premium-{preset.lower()}"{editable_attr(f"section.{key}.insight.main", "INSIGHT_CARD", "box")}><div class="premium-icon"{editable_attr(f"section.{key}.icon", "ICON", "scale")}>{icon}</div><div class="premium-copy"><small>Hallazgo clave</small><h3>{escape(str(section.get("title") or "Resultado destacado"))}</h3>{metric}<div class="metric-chips"{editable_attr(f"section.{key}.chips", "METRIC_CHIPS", "box")}>{chips}</div></div></aside>'
