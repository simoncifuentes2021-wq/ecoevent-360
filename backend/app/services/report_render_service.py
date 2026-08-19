"""Compose safe, client-ready editorial report documents."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

from app.services import file_storage_service, report_chart_service
from app.services.report_page_planner import plan_pages, visible_section

DEFAULT_THEME = {
    "primary_color": "#12372A",
    "secondary_color": "#2D6A4F",
    "accent_color": "#95D5B2",
    "background_color": "#F4F7F5",
    "text_color": "#15231D",
    "muted_color": "#61736A",
    "cover_style": "DARK_OVERLAY",
    "header_style": "MINIMAL",
    "footer_style": "PAGE_NUMBER",
    "show_page_numbers": True,
    "show_event_name_in_footer": True,
}
TEMPLATE_THEMES = {
    "ENVIRONMENTAL_PREMIUM": {},
    "ENVIRONMENTAL_STORY": {
        "primary_color": "#204D20",
        "secondary_color": "#34883A",
        "accent_color": "#69B849",
        "background_color": "#EFFBE8",
        "text_color": "#173D1B",
        "muted_color": "#58705B",
    },
    "BIKE_ZONE": {
        "primary_color": "#102F2B",
        "secondary_color": "#00A878",
        "accent_color": "#8EF0CF",
    },
    "OPERATIONS": {
        "primary_color": "#172554",
        "secondary_color": "#2563EB",
        "accent_color": "#93C5FD",
    },
    "EXECUTIVE": {
        "primary_color": "#18181B",
        "secondary_color": "#52525B",
        "accent_color": "#D4AF37",
    },
    "COMPLETE": {
        "primary_color": "#163A34",
        "secondary_color": "#3A7D65",
        "accent_color": "#D7F171",
    },
}


@dataclass(frozen=True)
class ReportRenderDocument:
    report: dict[str, Any]
    event: dict[str, Any]
    show: dict[str, Any] | None
    client: dict[str, Any]
    theme: dict[str, Any]
    sections: tuple[dict[str, Any], ...]
    evidences: tuple[dict[str, Any], ...]
    publication: dict[str, Any]
    editorial_config: dict[str, Any] = field(default_factory=dict)


def normalize_theme(raw: dict | None) -> dict:
    import re

    theme = {**DEFAULT_THEME, **(raw or {})}
    for key in (
        "primary_color",
        "secondary_color",
        "accent_color",
        "background_color",
        "text_color",
        "muted_color",
    ):
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(theme[key])):
            raise ValueError(f"Invalid theme color: {key}")
    return theme


def theme_for_template(template_key: str, raw: dict | None) -> dict:
    return normalize_theme({**TEMPLATE_THEMES.get(template_key, {}), **(raw or {})})


def evidence_asset(reference: str, mime: str | None) -> tuple[str | None, str | None]:
    try:
        obj = file_storage_service.get_stored_object(reference)
        if obj.size > 10 * 1024 * 1024 or obj.content_type not in {
            "image/jpeg",
            "image/png",
            "image/webp",
        }:
            return None, "Imagen omitida por formato o tamaño"
        encoded = base64.b64encode(obj.content).decode("ascii")
        return f"data:{obj.content_type};base64,{encoded}", None
    except Exception:
        return None, "Evidencia no disponible"


def build_html(document: ReportRenderDocument) -> str:
    theme = document.theme
    evidence_by_section: dict[str | None, list[dict]] = {}
    for item in document.evidences:
        evidence_by_section.setdefault(item.get("section_key"), []).append(item)
    all_photos = [item for item in document.evidences if item.get("uri")]
    sections = [
        visible_section(item)
        for item in document.sections
        if item.get("is_enabled") and item.get("section_type") != "COVER"
    ]
    by_key = {item["section_key"]: item for item in sections}
    plans = plan_pages(sections, document.report["template_key"], document.editorial_config)
    pages = [
        {
            "recipe": plan.recipe.value,
            "sections": [by_key[key] for key in plan.section_keys if key in by_key],
        }
        for plan in plans
        if plan.recipe.value != "COVER_HERO"
    ]
    page_html = "".join(
        _page_html(page, evidence_by_section, all_photos, theme, index + 1)
        for index, page in enumerate(pages)
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        + _styles(document)
        + f"</style><title>{escape(document.report['title'])}</title></head><body>"
        + _cover_html(document, all_photos)
        + page_html
        + "</body></html>"
    )


def _styles(document: ReportRenderDocument) -> str:
    t = document.theme
    return f"""
    @page {{size:A4;margin:0}} *{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
    body{{font-family:Arial,'Helvetica Neue',sans-serif;color:{t["text_color"]};font-size:10.5pt;line-height:1.45;background:#fff}}
    h1,h2,h3,p,figure{{margin-top:0}} .page{{height:297mm;padding:20mm 17mm 17mm;position:relative;overflow:hidden;page-break-after:always;background:#fff}}
    .page:last-child{{page-break-after:auto}} .page::after{{content:'';position:absolute;right:-30mm;top:-30mm;width:85mm;height:85mm;border-radius:50%;background:{t["background_color"]};z-index:0}}
    .page>*{{position:relative;z-index:1}} .cover{{height:297mm;padding:24mm;display:flex;flex-direction:column;justify-content:space-between;color:white;page-break-after:always;background-color:{t["primary_color"]};background-size:cover;background-position:center;position:relative;overflow:hidden}}
    .cover::before{{content:'';position:absolute;inset:0;background:linear-gradient(120deg,{t["primary_color"]}F5 10%,{t["primary_color"]}B8 58%,#0004)}} .cover::after{{content:'';position:absolute;width:155mm;height:155mm;border:1px solid {t["accent_color"]}77;border-radius:50%;right:-65mm;top:-30mm}}
    .cover>*{{position:relative;z-index:2}} .brand{{font-size:9pt;font-weight:800;letter-spacing:.24em;text-transform:uppercase}} .cover-copy{{max-width:168mm}}
    .cover.side-photo{{background-size:52% 100%;background-position:right center;background-repeat:no-repeat}} .cover.side-photo::before{{background:linear-gradient(90deg,{t["primary_color"]} 0 52%,{t["primary_color"]}EE 64%,#0002)}}
    .cover.editorial-cover{{justify-content:center}} .cover.editorial-cover .cover-copy{{border-left:2mm solid {t["accent_color"]};padding-left:10mm}}
    .cover.minimal-premium{{color:{t["text_color"]};background:{t["background_color"]}!important}} .cover.minimal-premium::before{{display:none}} .cover.minimal-premium .cover-meta,.cover.minimal-premium .cover-meta strong{{color:{t["text_color"]}}}
    .cover h1{{font-size:47pt;letter-spacing:-.045em;line-height:.94;margin:0 0 10mm;max-width:165mm}} .cover-line{{width:25mm;height:2mm;background:{t["accent_color"]};margin-bottom:8mm}}
    .cover-meta{{display:grid;grid-template-columns:1fr 1fr;gap:8mm;font-size:11pt;color:#eef7f2}} .cover-meta strong{{display:block;color:white;font-size:14pt}}
    .folio{{position:absolute;left:17mm;right:17mm;bottom:7mm;display:flex;justify-content:space-between;align-items:center;font-size:7.5pt;color:{t["muted_color"]};letter-spacing:.05em}}
    .folio b{{color:{t["secondary_color"]}}} .page-head{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:9mm;padding-bottom:4mm;border-bottom:1px solid #dce5e0}}
    .chapter{{font-size:8pt;font-weight:800;letter-spacing:.2em;text-transform:uppercase;color:{t["secondary_color"]}}} .page-head span:last-child{{font-size:8pt;color:{t["muted_color"]}}}
    h2{{font-size:31pt;line-height:1;letter-spacing:-.035em;color:{t["primary_color"]};margin-bottom:6mm}} h3{{font-size:17pt;line-height:1.08;color:{t["primary_color"]};margin-bottom:4mm}}
    .lead{{font-size:12.5pt;line-height:1.55;color:{t["muted_color"]};max-width:155mm}} .blocks{{display:grid;gap:8mm}} .blocks.two-up{{grid-template-columns:1fr 1fr;align-items:start}}
    .editorial-block{{break-inside:avoid}} .editorial-block.compact{{padding:7mm;background:{t["background_color"]};border-radius:2mm}} .section-rule{{width:13mm;height:1.5mm;background:{t["accent_color"]};margin-bottom:4mm}}
    .kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin:6mm 0}} .kpi{{min-height:31mm;padding:5mm;background:{t["background_color"]};border-radius:2mm;display:flex;flex-direction:column;justify-content:space-between}}
    .kpi:nth-child(1){{grid-column:span 2;background:{t["primary_color"]};color:white}} .kpi strong{{font-size:30pt;line-height:.95;letter-spacing:-.04em;color:{t["primary_color"]}}} .kpi:nth-child(1) strong{{font-size:43pt;color:white}}
    .kpi span{{font-size:8pt;text-transform:uppercase;letter-spacing:.08em;color:{t["muted_color"]}}} .kpi:nth-child(1) span{{color:{t["accent_color"]}}}
    .metrics{{columns:2;column-gap:10mm}} .metric{{display:flex;justify-content:space-between;gap:5mm;padding:2.8mm 0;border-bottom:1px solid #d8e2dd;break-inside:avoid}} .metric span{{color:{t["muted_color"]}}}
    .feature{{margin:0 -17mm;padding:14mm 17mm;background:{t["primary_color"]};color:white;min-height:206mm}} .feature h2,.feature h3{{color:white}} .feature .lead,.feature .metric span{{color:#d6e6de}} .feature .metric{{border-color:#ffffff33}}
    .feature-grid{{display:grid;grid-template-columns:1.05fr .95fr;gap:10mm;align-items:start}} .feature-number{{font-size:54pt;line-height:.9;font-weight:800;letter-spacing:-.05em;color:{t["accent_color"]}}} .feature-number small{{font-size:14pt;letter-spacing:0}}
    .chart-panel{{background:white;border-radius:2mm;padding:5mm;color:{t["text_color"]}}} svg{{width:100%;height:auto;max-height:105mm}}
    .photos{{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin-top:5mm}} figure{{margin:0;break-inside:avoid}} figure:first-child:nth-last-child(1){{grid-column:span 2}} figure img{{width:100%;height:70mm;object-fit:cover;border-radius:1.5mm}} .hero-photo img{{height:112mm}} figcaption{{padding-top:1.5mm;font-size:7.5pt;color:{t["muted_color"]}}} .feature figcaption{{color:#c9dbd2}}
    .photo-strip{{display:grid;grid-template-columns:1.35fr .65fr;gap:4mm}} .photo-strip figure:first-child img{{height:105mm}} .photo-strip figure:not(:first-child) img{{height:50.5mm}} .feature-visual{{display:grid;gap:4mm}} .feature-visual figure img{{height:78mm}} .feature-visual .chart-panel svg{{max-height:65mm}}
    .list{{display:grid;gap:2mm}} .list-row{{display:grid;grid-template-columns:1fr auto;gap:5mm;padding:3mm 0;border-bottom:1px solid #d8e2dd}} .list-row strong{{font-size:13pt;color:{t["primary_color"]}}}
    .quote{{font-size:19pt;line-height:1.35;color:{t["primary_color"]};padding:9mm 0 9mm 9mm;border-left:2mm solid {t["accent_color"]}}} .warning{{padding:8mm;background:{t["background_color"]};color:{t["muted_color"]};text-align:center}}
    .layout-two-column .section-body,.layout-text-image .section-body{{display:grid;grid-template-columns:1fr 1fr;gap:7mm}} .layout-hero-image-text{{background:{t["primary_color"]};color:white;padding:8mm;border-radius:2mm}} .layout-hero-image-text h3{{color:white}}
    .layout-editorial .section-copy{{font-size:15pt;line-height:1.6}} .layout-metric-list .metrics{{columns:1}} .layout-photo-grid .section-media{{order:-1}} .layout-feature-chart{{border-top:2mm solid {t["accent_color"]}}} .layout-big-numbers .kpi strong{{font-size:38pt}}
    .layout-hero-image-text .section-media img{{height:62mm}} .layout-text-image .section-media img{{height:52mm}} .layout-photo-grid .photos{{grid-template-columns:repeat(2,1fr)}}
    .feature.layout-text-image .feature-grid{{grid-template-columns:.85fr 1.15fr}} .feature.layout-photo-grid .chart-panel{{display:none}} .feature.layout-metric-list .feature-number{{font-size:36pt}} .feature.layout-kpi-grid .metrics{{columns:1}}
    .environmental-story{{display:grid;grid-template-columns:.9fr 1.1fr;gap:7mm;align-items:center}}
    .environmental-title span{{font-size:8pt;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:{t["secondary_color"]}}}
    .environmental-title h2{{font-size:40pt;margin:3mm 0 0}}
    .environmental-portraits{{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin:0}}
    .environmental-portraits figure img{{height:58mm;border-radius:50%;border:2mm solid white;box-shadow:0 2mm 8mm #173d1b22}}
    .environmental-panels{{grid-column:1/-1;display:grid;grid-template-columns:1.15fr .85fr;gap:0;border-radius:3mm;overflow:hidden;min-height:112mm}}
    .environmental-panel{{padding:9mm;color:white;overflow:hidden}} .environmental-panel h3{{font-size:28pt;color:white}}
    .waste-panel{{background:{t["primary_color"]}}} .bike-panel{{background:{t["accent_color"]}}}
    .environmental-panel .list-row{{border-color:#ffffff38}} .environmental-panel .list-row strong,.environmental-panel .list-row span{{color:white;font-size:10pt}}
    .environmental-panel .kpis{{grid-template-columns:1fr;margin:4mm 0}} .environmental-panel .kpi{{min-height:25mm;background:#ffffff22}}
    .environmental-panel .kpi:nth-child(1){{grid-column:auto;background:#ffffff22}} .environmental-panel .kpi strong,.environmental-panel .kpi:nth-child(1) strong{{font-size:30pt;color:white}}
    .environmental-panel .kpi span,.environmental-panel .kpi:nth-child(1) span{{color:white}}
    .carbon-story{{display:grid;grid-template-columns:1.05fr .9fr .8fr;min-height:211mm;border-radius:3mm;overflow:hidden;background:{t["primary_color"]};color:white}}
    .carbon-story>article{{padding:10mm 7mm;overflow:hidden}} .carbon-story h2,.carbon-story h3{{color:white}}
    .carbon-story h2{{font-size:31pt}} .carbon-story h3{{font-size:20pt;overflow-wrap:anywhere;hyphens:auto}}
    .carbon-panel{{background:{t["primary_color"]}}} .equivalence-panel{{background:{t["accent_color"]}}}
    .carbon-story .metrics{{columns:1}} .carbon-story .metric{{display:block;border-color:#ffffff36;padding:3mm 0}}
    .carbon-story .metric span,.carbon-story .metric strong{{display:block;color:white}}
    .carbon-story .metric strong{{font-size:14pt;margin-top:1mm}} .carbon-story .list-row{{display:block;border-color:#ffffff36}}
    .carbon-story .list-row span,.carbon-story .list-row strong{{display:block}} .carbon-story .list-row strong{{color:white;font-size:11pt;margin-top:1mm}} .equivalence-panel p{{font-size:9pt;line-height:1.5;margin-top:7mm}}
    .carbon-cards{{display:grid;gap:3mm}} .carbon-card{{display:grid;grid-template-columns:7mm 1fr;gap:3mm;padding:4mm;background:white;color:{t["primary_color"]};border-radius:2.5mm}}
    .carbon-check{{display:grid;width:5mm;height:5mm;place-items:center;border-radius:50%;background:{t["primary_color"]};color:white;font-size:8pt;font-weight:900;margin-top:1mm}}
    .carbon-card h4{{font-size:11pt;line-height:1.15;margin:0 0 1mm}} .carbon-card strong{{display:block;font-size:10pt;line-height:1.2;margin-bottom:1mm}}
    .carbon-card p{{font-size:7.5pt;line-height:1.35;margin:0;color:{t["text_color"]}}}
    .impact-official{{display:grid;grid-template-columns:1.08fr .92fr;gap:6mm;align-items:stretch}} .impact-official .impact-kpis{{display:grid;grid-template-columns:repeat(2,1fr);gap:3mm}}
    .impact-official .impact-card{{min-height:27mm;border:1px solid {t["accent_color"]};border-radius:3mm;padding:4mm;background:white;display:flex;flex-direction:column;justify-content:space-between}} .impact-card span{{display:block;color:{t["muted_color"]};font-size:8pt}} .impact-card strong{{display:flex;align-items:baseline;gap:1.5mm;margin-top:2mm;font-size:17pt;line-height:1;color:{t["primary_color"]};white-space:nowrap}} .impact-card strong small{{font-size:9pt;font-weight:700}}
    .impact-trace{{border-radius:3mm;background:{t["primary_color"]};color:white;padding:6mm;min-height:117mm}} .impact-trace h3{{color:white;font-size:19pt}} .impact-trace p{{font-size:7.5pt;line-height:1.45}} .impact-trace li{{margin:2mm 0;font-size:7.5pt;line-height:1.35}}
    .impact-details{{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin-top:6mm}} .impact-detail{{border-radius:3mm;background:{t["background_color"]};padding:5mm;min-height:34mm}} .impact-detail h4{{margin:0 0 2mm;color:{t["primary_color"]};font-size:11pt}} .impact-detail p{{margin:1mm 0;font-size:7.5pt;line-height:1.4;color:{t["muted_color"]}}} .impact-pill{{display:inline-block;margin:1mm 1mm 0 0;padding:1.5mm 2.5mm;border-radius:99px;background:white;font-size:7pt;color:{t["primary_color"]}}} .impact-disclaimer{{margin-top:5mm;padding:3mm 4mm;border-left:1.5mm solid {t["accent_color"]};font-size:7.5pt;color:{t["muted_color"]};background:{t["background_color"]}}}
    .carbon-visual,.carbon-photo,.carbon-photo figure{{height:100%;margin:0}} .carbon-photo{{display:block}}
    .carbon-photo figure img{{height:211mm;border-radius:0;object-fit:cover}} .carbon-photo figcaption{{display:none}}
    .carbon-story{{grid-template-columns:1.05fr 1.05fr .65fr}} .carbon-story h3{{font-size:18pt;overflow-wrap:normal;hyphens:none}}
    p{{orphans:3;widows:3}} .editorial-block,.kpi,figure,.metric{{break-inside:avoid-page}}
    """


def _cover_html(document: ReportRenderDocument, photos: list[dict]) -> str:
    cover = next((item for item in document.sections if item.get("section_type") == "COVER"), {})
    field_records = {
        item.get("key"): item for item in (cover.get("content") or {}).get("fields", [])
    }

    def cover_value(key: str, fallback: str) -> str:
        field = field_records.get(key)
        if field and field.get("is_visible", True) is False:
            return ""
        return str(field.get("value") if field and field.get("value") is not None else fallback)

    selected_id = str(document.editorial_config.get("cover_evidence_id") or "")
    photo = next(
        (item for item in photos if str(item.get("evidence_id")) == selected_id),
        photos[0] if photos else None,
    )
    style = f' style="background-image:url({photo["uri"]})"' if photo else ""
    cover_style = document.editorial_config.get("cover_style", "FULL_PHOTO")
    class_name = {
        "SIDE_PHOTO": "side-photo",
        "EDITORIAL": "editorial-cover",
        "MINIMAL_PREMIUM": "minimal-premium",
    }.get(cover_style, "full-photo")
    title = cover_value("title", document.report["title"])
    client = cover_value("client", document.client["name"])
    event = cover_value("event", document.event["name"])
    date = cover_value("date", document.event["date"])
    venue = cover_value("venue", "")
    subtitle = (cover.get("content") or {}).get("text") or "Reporte de impacto"
    show = (
        f"<strong>{escape(document.show['name'])}</strong>Show seleccionado"
        if document.show
        else "<strong>Reporte integral</strong>Alcance evento"
    )
    return f'''<section class="cover {class_name}"{style}><div class="brand">EcoEvent 360 · {escape(str(subtitle))}</div><div class="cover-copy"><div class="cover-line"></div><h1>{escape(title)}</h1><div class="cover-meta"><div><strong>{escape(client)}</strong>{escape(event)}</div><div>{show}<br>{escape(date)}<br>{escape(venue)}</div></div></div></section>'''


def _page_html(
    page: dict, evidence_map: dict, all_photos: list[dict], theme: dict, number: int
) -> str:
    sections = page["sections"]
    recipe = page["recipe"]
    title = sections[0]["title"] if sections else "Información del reporte"
    section_photos = [
        photo
        for section in sections
        for photo in evidence_map.get(section.get("section_key"), [])
        if photo.get("uri")
    ]
    photos = section_photos or (
        all_photos[:4]
        if recipe.startswith("FEATURE_")
        or recipe in {"KPI_SUMMARY", "ENVIRONMENTAL_MANAGEMENT", "CARBON_EQUIVALENCES"}
        else []
    )
    if recipe == "PHOTO_STORY":
        content = _evidence_html(sections[0], photos)
    elif recipe == "ENVIRONMENTAL_MANAGEMENT":
        content = _environmental_management_html(sections, photos)
    elif recipe == "ENVIRONMENTAL_OVERVIEW":
        content = _environmental_impact_html(sections)
    elif recipe == "CARBON_EQUIVALENCES":
        content = _carbon_equivalences_html(sections, photos)
    elif recipe in {"BIKE_ZONE_FEATURE", "WASTE_FEATURE", "CARBON_FEATURE", "FORMS_INSIGHTS"}:
        content = _feature_html(sections, photos, theme)
    elif recipe == "EXECUTIVE_OVERVIEW":
        content = _summary_html(sections, photos, theme)
    elif recipe == "EDITORIAL_CLOSE":
        content = _conclusion_html(sections, theme)
    elif recipe == "EMPTY":
        content = '<div class="quote">Este reporte está preparado para crecer con la información del evento.</div>'
    else:
        content = _mixed_html(sections, photos, theme)
    return f"""<section class="page recipe-{recipe.lower()}"><header class="page-head"><span class="chapter">{escape(title)}</span><span>EcoEvent 360</span></header>{content}<footer class="folio"><span>Impacto · operación · evidencia</span><b>{number:02d}</b></footer></section>"""


def _environmental_management_html(sections: list[dict], photos: list[dict]) -> str:
    waste = next((item for item in sections if item.get("section_type") == "WASTE"), None)
    bike = next((item for item in sections if item.get("section_type") == "BIKE_ZONE"), None)
    waste_content = (waste or {}).get("content") or {}
    bike_content = (bike or {}).get("content") or {}
    waste_values = (waste_content.get("items") or [])[:8]
    bike_fields = (bike_content.get("fields") or [])[:3]
    return (
        '<div class="environmental-story">'
        '<div class="environmental-title"><span>Reporte de impacto</span>'
        "<h2>Gestión<br>Ambiental</h2></div>"
        f"{_photos(photos[:2], 'environmental-portraits')}"
        '<div class="environmental-panels">'
        f'<article class="environmental-panel waste-panel"><h3>Reciclaje</h3>{_items(waste_values) if waste_values else _metrics((waste_content.get("fields") or [])[:8])}</article>'
        f'<article class="environmental-panel bike-panel"><h3>Bicicletero</h3>{_kpis(bike_fields)}'
        f"<p>{_safe_text(bike_content.get('text') or 'Movilidad sustentable durante el evento.')}</p></article>"
        "</div></div>"
    )


def _environmental_impact_html(sections: list[dict]) -> str:
    section = sections[0]
    content = section.get("content") or {}
    snapshot = section.get("source_snapshot") or {}
    official = snapshot.get("official_data") or content.get("official_data") or {}
    precision = {
        "energy_kwh": 2,
        "fuel_avoided_l": 2,
        "co2e_baseline_kg": 2,
        "co2e_actual_kg": 2,
        "co2e_avoided_kg": 2,
        "pm25_avoided_kg": 5,
        "pm10_avoided_kg": 5,
        "nox_avoided_kg": 5,
    }
    fields = content.get("fields") or []
    cards = "".join(
        '<article class="impact-card">'
        f"<span>{escape(str(field.get('label') or 'Indicador'))}</span>"
        f"<strong>{escape(_display_number(field.get('value'), precision.get(str(field.get('key')), 2), str(field.get('key')) in {'energy_kwh', 'fuel_avoided_l'}))}"
        f"<small>{escape(str(field.get('unit') or ''))}</small></strong>"
        "</article>"
        for field in fields[:8]
    )
    actions = official.get("actions") or []
    action_list = "".join(
        f"<li>{escape(str(item.get('name')))} · {escape(str(item.get('session_name')))} · "
        f"{escape(str(item.get('methodology') or 'Sin metodología'))}</li>"
        for item in actions[:8]
    )
    sources = official.get("sources") or []
    source_list = (
        "".join(
            f"<li>{escape(str(item.get('source') or 'Fuente documentada'))}"
            f"{' (' + escape(str(item.get('year'))) + ')' if item.get('year') else ''}</li>"
            for item in sources[:4]
        )
        or "<li>Sin factores aprobados disponibles.</li>"
    )
    breakdown = official.get("breakdown") or []
    breakdown_html = (
        "".join(
            '<span class="impact-pill">'
            f"{escape(str(item.get('session_name') or item.get('scope_name') or 'Evento'))}: "
            f"{escape(_display_number((item.get('metrics') or {}).get('co2e_avoided_kg'), 2))} kg CO2e</span>"
            for item in breakdown[:6]
        )
        or "<p>El resultado corresponde al alcance completo del evento.</p>"
    )
    methodologies = official.get("methodologies") or []
    methodology_html = (
        "".join(
            f"<p><b>{escape(str(item.get('name') or item.get('title') or 'Metodología aprobada'))}</b></p>"
            for item in methodologies[:3]
        )
        or "<p>La metodología utilizada se detalla en la trazabilidad aprobada.</p>"
    )
    equivalences = official.get("equivalences") or []
    equivalence_html = "".join(
        '<span class="impact-pill">'
        f"{escape(str(item.get('label') or item.get('name') or 'Equivalencia'))}: "
        f"{escape(_display_number(item.get('value'), 2, True))} {escape(str(item.get('unit') or ''))}</span>"
        for item in equivalences[:4]
    )
    disclaimer = official.get("disclaimer") or content.get("text") or ""
    return (
        "<h2>Impacto ambiental evitado</h2>"
        '<div class="impact-official"><div class="impact-kpis">'
        f"{cards}</div><aside class='impact-trace'><h3>Trazabilidad aprobada</h3>"
        f"<p>{escape(str(len(actions)))} acciones aprobadas. Solo estos resultados forman parte del reporte oficial.</p>"
        f"<ul>{action_list}</ul><p><b>Fuentes documentadas</b></p><ul>{source_list}</ul>"
        "</aside></div>"
        '<div class="impact-details">'
        f'<article class="impact-detail"><h4>Resultados por alcance</h4>{breakdown_html}</article>'
        f'<article class="impact-detail"><h4>Metodologías y equivalencias</h4>{methodology_html}{equivalence_html}</article>'
        "</div>"
        f'<div class="impact-disclaimer">{escape(str(disclaimer))}</div>'
    )


def _display_number(value: Any, digits: int = 2, trim: bool = False) -> str:
    """Format report values for people without changing the stored calculation."""
    if value is None:
        return "—"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    formatted = f"{number:.{digits}f}"
    if trim:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted.replace(".", ",")


def _carbon_equivalences_html(sections: list[dict], photos: list[dict]) -> str:
    carbon = next((item for item in sections if item.get("section_type") == "CARBON"), None)
    equivalents = [item for item in sections if item.get("section_type") == "CUSTOM"]
    carbon_content = (carbon or {}).get("content") or {}
    equivalent_fields = [
        field
        for section in equivalents
        for field in ((section.get("content") or {}).get("fields") or [])
    ][:6]
    equivalent_text = next(
        (
            (section.get("content") or {}).get("text")
            for section in equivalents
            if (section.get("content") or {}).get("text")
        ),
        "Equivalencias ambientales calculadas a partir de los resultados del evento.",
    )
    return (
        '<div class="carbon-story">'
        '<article class="carbon-panel"><h2>Huella de<br>Carbono</h2>'
        f"{_carbon_cards(carbon_content.get('fields') or [], carbon_content.get('items') or [])}</article>"
        '<article class="equivalence-panel"><h3>Eco-<br>equivalencias</h3>'
        f"{_metrics(equivalent_fields)}<p>{_safe_text(equivalent_text)}</p></article>"
        f'<aside class="carbon-visual">{_photos(photos[:1], "carbon-photo")}</aside></div>'
    )


def _carbon_cards(fields: list[dict], items: list[dict]) -> str:
    records = [
        {
            "label": field.get("label"),
            "value": field.get("value"),
            "unit": field.get("unit"),
            "description": field.get("description"),
        }
        for field in fields
    ] + items
    cards = []
    for item in records[:7]:
        value = ""
        if item.get("value") is not None:
            value = (
                f"<strong>{escape(str(item['value']))} "
                f"{escape(str(item.get('unit') or ''))}</strong>"
            )
        description = item.get("description")
        body = f"<p>{_safe_text(description)}</p>" if description else value
        if description and value:
            body = value + body
        cards.append(
            '<article class="carbon-card"><span class="carbon-check">✓</span>'
            f"<div><h4>{escape(str(item.get('label') or 'Indicador'))}</h4>{body}</div></article>"
        )
    return f'<div class="carbon-cards">{"".join(cards)}</div>'


def _summary_html(sections: list[dict], photos: list[dict], theme: dict) -> str:
    fields = [
        field for section in sections for field in (section.get("content") or {}).get("fields", [])
    ][:6]
    text = next(
        (
            (section.get("content") or {}).get("text")
            for section in sections
            if (section.get("content") or {}).get("text")
        ),
        "Una lectura ejecutiva de los principales resultados del evento.",
    )
    items = [
        item for section in sections for item in (section.get("content") or {}).get("items", [])
    ]
    return f'<h2>El impacto,<br>en perspectiva.</h2><p class="lead">{_safe_text(text)}</p>{_kpis(fields[:6])}{_metrics(fields[6:])}{_items(items)}{_photos(photos[:2], "photos")}'


def _evidence_html(section: dict, photos: list[dict]) -> str:
    text = (
        (section.get("content") or {}).get("text")
        or "Una mirada cercana a la operación, las personas y los resultados que hicieron posible el evento."
    )
    gallery = (
        _photos(photos[:4], "photos")
        or '<div class="warning">Las nuevas evidencias aparecerán aquí al ser incorporadas.</div>'
    )
    content = section.get("content") or {}
    variant = str(section.get("layout_variant") or "PHOTO_GRID").lower().replace("_", "-")
    return f'<div class="feature layout-{variant}"><div class="section-rule"></div><h2>{escape(section["title"])}</h2><p class="lead">{_safe_text(text)}</p>{_metrics(content.get("fields") or [])}{_items(content.get("items") or [])}{gallery}</div>'


def _feature_html(sections: list[dict], photos: list[dict], theme: dict) -> str:
    section = sections[0]
    content = section.get("content") or {}
    fields = content.get("fields") or []
    items = content.get("items") or []
    section_type = section.get("section_type")
    variant = str(section.get("layout_variant") or "FEATURE_CHART").lower().replace("_", "-")
    intro = _safe_text(content.get("text") or _feature_intro(section_type))
    chart = report_chart_service.bar_chart(items, theme["accent_color"])
    photo_html = _photos(photos[:2], "photos")
    chart_html = f'<div class="chart-panel">{chart}</div>' if chart else ""
    visual = f'<div class="feature-visual">{photo_html}{chart_html}</div>'
    if not visual:
        visual = '<div class="chart-panel"><div class="warning">Los indicadores se actualizarán al incorporar nuevos registros.</div></div>'
    lead = fields[0] if fields else None
    number = f'<div class="feature-number">{escape(str(lead.get("value") if lead and lead.get("value") is not None else "—"))}<small> {escape(str(lead.get("unit") or "")) if lead else ""}</small><span>{escape(str(lead.get("label") or "")) if lead else ""}</span></div>'
    companions = "".join(
        f'<article class="editorial-block"><h3>{escape(item["title"])}</h3>{_metrics((item.get("content") or {}).get("fields") or [])}</article>'
        for item in sections[1:]
    )
    indicators = (
        _kpis(fields[:6])
        if section.get("layout_variant") == "KPI_GRID"
        else f"{number}{_metrics(fields[1:])}"
    )
    return f'<div class="feature layout-{variant}"><div class="section-rule"></div><h2>{escape(section["title"])}</h2><div class="feature-grid"><div>{indicators}<p class="lead">{intro}</p>{_items(items)}{companions}</div><div>{visual}</div></div></div>'


def _mixed_html(sections: list[dict], photos: list[dict], theme: dict) -> str:
    blocks = []
    for section in sections:
        content = section.get("content") or {}
        fields = content.get("fields") or []
        items = content.get("items") or []
        copy = (
            f'<div class="section-copy"><p>{_safe_text(content.get("text"))}</p></div>'
            if content.get("text")
            else '<div class="section-copy"></div>'
        )
        fields_html = (
            _kpis(fields[:4])
            if section.get("layout_variant") in {"KPI_GRID", "BIG_NUMBERS"}
            else _metrics(fields)
        )
        media = ""
        if section.get("layout_variant") in {"HERO_IMAGE_TEXT", "TEXT_IMAGE", "PHOTO_GRID"}:
            amount = 4 if section.get("layout_variant") == "PHOTO_GRID" else 1
            media = f'<div class="section-media">{_photos(photos[:amount], "photos")}</div>'
        chart = report_chart_service.bar_chart(items, theme["accent_color"])
        if section.get("layout_variant") == "FEATURE_CHART" and chart:
            media = f'<div class="section-media chart-panel">{chart}</div>'
        body = f'<div class="section-body">{copy}<div class="section-fields">{fields_html}{_items(items)}</div>{media}</div>'
        variant = str(section.get("layout_variant") or "EDITORIAL").lower().replace("_", "-")
        blocks.append(
            f'<article class="editorial-block compact layout-{variant}"><div class="section-rule"></div><h3>{escape(section["title"])}</h3>{body}</article>'
        )
    columns = "two-up" if len(blocks) > 1 else ""
    photo_html = _photos(photos[:3], "photo-strip") if photos else ""
    return f'<h2>Resultados que<br>construyen historia.</h2>{photo_html}<div class="blocks {columns}">{"".join(blocks)}</div>'


def _conclusion_html(sections: list[dict], theme: dict) -> str:
    blocks = []
    for section in sections:
        content = section.get("content") or {}
        blocks.append(
            f'<article><h3>{escape(section["title"])}</h3><div class="quote">{_safe_text(content.get("text") or "Los resultados abren oportunidades concretas para la próxima edición.")}</div>{_metrics(content.get("fields") or [])}</article>'
        )
    return f'<h2>Lo logrado es<br>el punto de partida.</h2><div class="blocks two-up">{"".join(blocks)}</div>'


def _kpis(fields: list[dict]) -> str:
    if not fields:
        return ""
    cards = "".join(
        f'<div class="kpi"><strong>{escape(str(field.get("value") if field.get("value") is not None else "—"))}</strong><span>{escape(str(field.get("unit") or ""))} {escape(str(field.get("label") or ""))}</span></div>'
        for field in fields
    )
    return f'<div class="kpis">{cards}</div>'


def _metrics(fields: list[dict]) -> str:
    if not fields:
        return ""
    rows = "".join(
        f'<div class="metric"><span>{escape(str(field.get("label") or ""))}</span><strong>{escape(str(field.get("value") if field.get("value") is not None else "—"))} {escape(str(field.get("unit") or ""))}</strong></div>'
        for field in fields[:12]
    )
    return f'<div class="metrics">{rows}</div>'


def _items(items: list[dict]) -> str:
    if not items:
        return ""
    rows = []
    for item in items[:8]:
        public_values = [value for key, value in item.items() if not key.startswith("_")]
        label = (
            item.get("label")
            or item.get("name")
            or (public_values[0] if public_values else "Detalle")
        )
        raw_value = item.get("value")
        if raw_value is None:
            raw_value = item.get("total_kg", item.get("total_kgco2e"))
        value = str(raw_value if raw_value is not None else "—")
        if item.get("unit"):
            value = f"{value} {item['unit']}"
        rows.append(
            f'<div class="list-row"><span>{escape(str(label))}</span><strong>{escape(value)}</strong></div>'
        )
    return f'<div class="list">{"".join(rows)}</div>'


def _photos(photos: list[dict], css_class: str) -> str:
    if not photos:
        return ""
    figures = "".join(
        f'<figure><img src="{photo["uri"]}"><figcaption>{escape(str(photo.get("caption") or "Evidencia del evento"))}</figcaption></figure>'
        for photo in photos
    )
    return f'<div class="{css_class}">{figures}</div>'


def _safe_text(value: Any) -> str:
    return escape(str(value or "")).replace("\n", "<br>")


def _feature_intro(section_type: str | None) -> str:
    return {
        "WASTE": "Materiales recuperados y decisiones operativas que reducen el impacto del evento.",
        "BIKE_ZONE": "Movilidad activa que conecta experiencia, comunidad y sostenibilidad.",
        "CARBON": "Una lectura clara de la huella y de las oportunidades de reducción.",
        "EVIDENCES": "La operación documentada a través de sus momentos y resultados.",
        "ECO_EQUIVALENCES": "El impacto traducido a referencias simples, cercanas y memorables.",
    }.get(section_type, "Resultados destacados del evento.")
