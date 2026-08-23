from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.ai import AIGeneration
from app.models.core import Report, User
from app.models.enums import ReportLayoutVariant
from app.services import report_builder_service, report_revision_service
from app.services.ai.contexts.reports import EDITORIAL_CAPABILITY
from app.services.ai.schemas import ReportAIEditorialPlan


def apply_plan(db: Session, report: Report, generation_id: UUID, edit_version: int, user: User):
    report_builder_service._assert_editable(report, edit_version)
    generation = db.get(AIGeneration, generation_id)
    if not generation or generation.capability != EDITORIAL_CAPABILITY or generation.subject_id != report.id or generation.status != "SUCCEEDED" or generation.requested_by != user.id:
        raise HTTPException(404, "Editorial AI proposal not found")
    plan = ReportAIEditorialPlan.model_validate(generation.output)
    revision = report_revision_service.create(
        db, report, user, edit_version, "Antes de aplicar optimizacion editorial con IA"
    )
    by_key = {section.section_key: section for section in report.sections}
    if set(plan.section_order) != {key for key, section in by_key.items() if section.is_enabled}:
        raise HTTPException(409, "La propuesta ya no coincide con las secciones visibles del informe")
    if plan.report_title_suggestion:
        report.title = plan.report_title_suggestion
    config = dict(report.editorial_config or {})
    config["mode"] = "CUSTOM"
    config["cover_style"] = plan.cover_style
    overrides = dict(config.get("page_overrides") or {})
    for item in plan.sections:
        section = by_key.get(item.section_key)
        if not section or not section.is_enabled:
            continue
        section.layout_variant = ReportLayoutVariant(item.layout_variant)
        if item.title_suggestion:
            section.title = item.title_suggestion
        if item.generated_text:
            content = dict(section.content or {})
            had_text = bool(content.get("text"))
            content["text"] = item.generated_text
            content["text_origin"] = "ENRICHED" if had_text else "GENERATED"
            content["ai_generation_id"] = str(generation.id)
            section.content = content
        override = {"mode": item.page_mode}
        if item.page_mode == "GROUP_WITH" and item.group_with in by_key:
            override["group_with"] = item.group_with
        overrides[item.section_key] = override
        section.updated_at = datetime.utcnow()
    config["page_overrides"] = overrides
    report.editorial_config = config
    ordered = [by_key[key] for key in plan.section_order]
    ordered.extend(section for section in report.sections if section.section_key not in plan.section_order)
    for index, section in enumerate(ordered):
        section.sort_order = index
    report.edit_version += 1
    report.updated_at = datetime.utcnow()
    db.commit()
    return revision, report_builder_service.get_editor(db, report.id, user)
