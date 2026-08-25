from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.models.ai import AIGeneration
from app.services import report_builder_service, report_revision_service
from app.services.ai.contexts.reports import ASSISTANT_CAPABILITY
from app.services.ai.schemas import ReportAIAssistantProposal


def proposal_diff(report, proposal: ReportAIAssistantProposal) -> list[dict]:
    changes = []
    current_preset = ((report.editorial_config or {}).get("visual_config") or {}).get("preset", "AUTO")
    if current_preset != proposal.recommended_preset:
        changes.append({"type": "preset", "key": "preset", "current": current_preset, "proposed": proposal.recommended_preset})
    by_key = {section.section_key: section for section in report.sections}
    for item in proposal.sections:
        current = by_key[item.section_key]
        if current.is_enabled != item.visible:
            changes.append({"type": "visibility", "key": item.section_key, "current": current.is_enabled, "proposed": item.visible})
        if current.sort_order != item.order:
            changes.append({"type": "order", "key": item.section_key, "current": current.sort_order, "proposed": item.order})
        if item.narrative is not None and item.narrative != (current.content or {}).get("text"):
            changes.append({"type": "narrative", "key": item.section_key, "current": (current.content or {}).get("text"), "proposed": item.narrative})
    return changes


def apply_proposal(db, report, generation_id: UUID, edit_version: int, user, accepted_section_keys=None, apply_preset=True):
    report_builder_service._assert_editable(report, edit_version)
    generation = db.scalar(select(AIGeneration).where(
        AIGeneration.id == generation_id, AIGeneration.subject_id == report.id,
        AIGeneration.capability == ASSISTANT_CAPABILITY, AIGeneration.status == "SUCCEEDED",
        AIGeneration.requested_by == user.id,
    ))
    if not generation:
        raise HTTPException(404, "AI report proposal not found")
    proposal = ReportAIAssistantProposal.model_validate(generation.output)
    revision = report_revision_service.create(db, report, user, edit_version, "Antes de aplicar propuesta IA premium")
    accepted = set(accepted_section_keys) if accepted_section_keys is not None else {item.section_key for item in proposal.sections}
    by_key = {section.section_key: section for section in report.sections}
    if apply_preset:
        config = dict(report.editorial_config or {})
        visual = dict(config.get("visual_config") or {})
        visual["preset"] = proposal.recommended_preset
        config["visual_config"] = visual
        report.editorial_config = config  # preserves page_overrides and manual section visuals
    for item in proposal.sections:
        if item.section_key not in accepted:
            continue
        section = by_key[item.section_key]
        section.is_enabled = item.visible
        section.sort_order = item.order
        if item.narrative is not None:
            content = dict(section.content or {})
            content["text"] = item.narrative
            content["text_origin"] = "ENRICHED" if content.get("text") else "GENERATED"
            content["ai_generation_id"] = str(generation.id)
            section.content = content
        section.updated_at = datetime.now(UTC).replace(tzinfo=None)
    for suggestion in proposal.evidence_suggestions:
        if suggestion.section_key not in accepted:
            continue
        evidence = next((item for item in report.evidences if item.evidence_id == suggestion.evidence_id), None)
        if evidence:
            evidence.section_id = by_key[suggestion.section_key].id
    generation.applied = True
    report.edit_version += 1
    report.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return revision, report_builder_service.get_editor(db, report.id, user)
