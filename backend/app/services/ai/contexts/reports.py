from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Report, ReportScope, ReportSection, User
from app.services import report_builder_service
from app.services.ai.schemas import ReportAIRequest
from app.services.ai.privacy import sanitize
from app.services.report_data_binding_registry import catalog
from app.services import report_visual_design_service
from app.services.ai.comparison_service import compare

CAPABILITY = "reports.section_draft"
EDITORIAL_CAPABILITY = "reports.editorial_plan"
SENSITIVE_KEYS = {"email", "phone", "telephone", "contact", "address", "rut", "dni", "password", "token", "full_name", "first_name", "last_name", "participant", "responder", "user_id"}


def _safe(value):
    return sanitize(value)


ASSISTANT_CAPABILITY = "reports.premium_assistant"


def _multishow_comparisons(db: Session, report: Report) -> tuple[dict, list[dict]]:
    show_reports = list(db.scalars(select(Report).where(
        Report.event_id == report.event_id, Report.scope == ReportScope.SHOW
    ).order_by(Report.created_at, Report.id)).unique().all())
    if len(show_reports) < 2:
        return {}, []
    snapshots = []
    for item in show_reports:
        values = {binding["key"]: binding for binding in catalog(item) if binding and binding["availability"] == "AVAILABLE" and isinstance(binding.get("value"), (int, float)) and not isinstance(binding.get("value"), bool)}
        snapshots.append((item, values))
    baseline, baseline_values = snapshots[0]
    sources, comparisons = {}, []
    for compared, compared_values in snapshots[1:]:
        for metric_key in sorted(set(baseline_values).intersection(compared_values)):
            left, right = baseline_values[metric_key], compared_values[metric_key]
            if left.get("unit") != right.get("unit"):
                continue
            result = compare(left["value"], right["value"])
            prefix = f"comparison.{baseline.session_id}.{compared.session_id}.{metric_key}"
            sources[f"{prefix}.baseline"] = {"value": result["baseline"], "unit": left.get("unit"), "source": metric_key, "show_id": str(baseline.session_id)}
            sources[f"{prefix}.comparison"] = {"value": result["comparison"], "unit": right.get("unit"), "source": metric_key, "show_id": str(compared.session_id)}
            sources[f"{prefix}.absolute_difference"] = {"value": result["absolute_difference"], "unit": left.get("unit"), "source": "backend_calculation"}
            if result["percentage_difference"] is not None:
                sources[f"{prefix}.percentage_difference"] = {"value": result["percentage_difference"], "unit": "%", "source": "backend_calculation"}
            comparisons.append({"metric_key": metric_key, "baseline_show_id": str(baseline.session_id), "comparison_show_id": str(compared.session_id), "unit": left.get("unit"), **result})
    return sources, comparisons


def build_report_assistant_context(db: Session, report_id: UUID, user: User, instructions: str):
    report = report_builder_service.get_editor(db, report_id, user)
    bindings = [item for item in catalog(report) if item and item["availability"] == "AVAILABLE"]
    sources = {item["key"]: {"value": item["value"], "unit": item["unit"], "source": item["source"]} for item in bindings}
    comparison_sources, comparisons = _multishow_comparisons(db, report)
    sources.update(comparison_sources)
    for section in report.sections:
        for field in (section.content or {}).get("fields") or []:
            if field.get("is_visible", True) and field.get("value") is not None:
                sources.setdefault(f"{section.section_key}.{field.get('key', 'metric')}", {"value": field["value"], "unit": field.get("unit"), "source": section.section_key})
        for index, item in enumerate((section.content or {}).get("items") or []):
            if item.get("_is_visible", True) is False:
                continue
            value = item.get("value", item.get("total_kg", item.get("total_kgco2e")))
            if value is not None:
                key = str(item.get("key") or item.get("metric_key") or index)
                sources.setdefault(f"{section.section_key}.items.{key}", {"value": value, "unit": item.get("unit"), "source": section.section_key, "show_id": item.get("show_id")})
    context = {
        "scope": {"event_id": str(report.event_id), "show_id": str(report.session_id) if report.session_id else None},
        "request": {"instructions": instructions},
        "current": {
            "report_id": str(report.id), "title": report.title, "preset": ((report.editorial_config or {}).get("visual_config") or {}).get("preset", "AUTO"),
            "sections": [{"section_key": s.section_key, "section_type": s.section_type.value, "visible": s.is_enabled, "order": s.sort_order, "premium_variant": report_visual_design_service.section_variant(((report.editorial_config or {}).get("visual_config") or {}).get("preset", "AUTO"), s.section_type.value) or "AUTO", "manual_visual": ((report.editorial_config or {}).get("section_visuals") or {}).get(s.section_key), "content": s.content} for s in report.sections],
        },
        "allowlists": {
            "presets": ["AUTO", *report_visual_design_service.PRESETS.keys()],
            "premium_variants": sorted({"AUTO", *[value for variants in report_visual_design_service.PRESET_SECTION_VARIANTS.values() for value in variants.values()]}),
            "variants_by_preset": {preset: {s.section_key: variants.get(s.section_type.value, "AUTO") for s in report.sections} for preset, variants in report_visual_design_service.PRESET_SECTION_VARIANTS.items()},
            "section_keys": [s.section_key for s in report.sections],
        },
        "sources": sources,
        "multishow_comparisons": comparisons,
        "evidences": [{"id": str(e.evidence_id), "section_key": next((s.section_key for s in report.sections if s.id == e.section_id), None), "caption": e.caption or e.evidence.description, "show_id": str(e.evidence.session_id) if e.evidence.session_id else None, "taken_at": e.evidence.taken_at.isoformat() if e.evidence.taken_at else None} for e in report.evidences if e.is_enabled],
    }
    return report, sanitize(context)


def build_report_section_context(
    db: Session, report_id: UUID, section_id: UUID, user: User, options: ReportAIRequest
) -> tuple[ReportSection, dict]:
    report = report_builder_service.get_editor(db, report_id, user)
    section = db.scalar(select(ReportSection).where(ReportSection.id == section_id, ReportSection.report_id == report.id))
    if not section:
        raise ValueError("Section not found")
    current_text = options.current_text if options.current_text is not None else (section.content or {}).get("text")
    context = {
        "scope": {"type": report.scope.value, "event_id": str(report.event_id), "show_id": str(report.session_id) if report.session_id else None},
        "section": {"key": section.section_key, "type": section.section_type.value, "title": section.title},
        "request": {"operation": options.operation, "style": options.style, "length": options.length},
        "effective_content": {
            "text": current_text,
            "fields": (section.content or {}).get("fields", []),
            "items": (section.content or {}).get("items", []),
        },
        "source_data": section.source_snapshot or {},
        "source_metadata": section.source_metadata or {},
    }
    if section.section_type.value in {"EXECUTIVE_SUMMARY", "CONCLUSION"}:
        context["source_data"] = {}
        context["included_sections"] = [
            {
                "key": item.section_key,
                "title": item.title,
                "effective_content": item.content,
            }
            for item in report.sections
            if item.is_enabled and item.id != section.id
        ]
    return section, _safe(context)


def build_report_editorial_context(db: Session, report_id: UUID, user: User, style: str, include_text_rewrites: bool):
    report = report_builder_service.get_editor(db, report_id, user)
    context = {
        "scope": {"type": report.scope.value, "event_id": str(report.event_id), "show_id": str(report.session_id) if report.session_id else None},
        "request": {"style": style, "include_text_rewrites": include_text_rewrites},
        "report": {"title": report.title, "template": report.template_key.value, "theme": report.theme, "editorial_config": report.editorial_config},
        "allowed_layouts": ["HERO_IMAGE_TEXT", "KPI_GRID", "TWO_COLUMN", "METRIC_LIST", "FEATURE_CHART", "PHOTO_GRID", "EDITORIAL", "TEXT_IMAGE", "BIG_NUMBERS"],
        "sections": [
            {
                "section_key": section.section_key,
                "section_type": section.section_type.value,
                "title": section.title,
                "layout_variant": section.layout_variant.value,
                "is_enabled": section.is_enabled,
                "sort_order": section.sort_order,
                "effective_content": section.content,
                "availability": (section.source_metadata or {}).get("availability"),
                "evidence_count": sum(1 for evidence in report.evidences if evidence.is_enabled and evidence.section_id == section.id),
            }
            for section in report.sections
        ],
    }
    return report, _safe(context)
