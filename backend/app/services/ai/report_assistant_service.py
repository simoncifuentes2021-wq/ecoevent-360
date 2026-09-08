from datetime import UTC, datetime
import re
import unicodedata
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.models.ai import AIGeneration
from app.services import report_builder_service, report_revision_service
from app.services.ai.contexts.reports import ASSISTANT_CAPABILITY
from app.services.ai.schemas import ReportAIAssistantProposal
from app.services import report_visual_audit_service


def _claim_text(claims) -> str:
    public = [_client_copy(claim.text) for claim in claims]
    return "\n".join(f"• {text}" for text in public if text)


SECTION_FINDING_TITLES = {
    "event_info": "Lectura del evento",
    "show_info": "Lectura de la función",
    "services": "Cobertura del servicio",
    "operations": "Ejecución destacada",
    "staff": "Síntesis del equipo",
    "tasks": "Estado de avance",
    "incidents": "Situaciones relevantes",
    "forms": "Resultados de participación",
    "bike_zone": "Uso del bicicletero",
    "waste": "Resultados de circularidad",
    "carbon": "Lectura de emisiones",
    "environmental_impact": "Impactos verificados",
    "preset_eco_equivalences": "Equivalencias comunicacionales",
    "evidences": "Registro documental",
    "recommendations": "Líneas de acción",
    "conclusion": "Balance final",
}


def _normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


_INTERNAL_COPY = re.compile(
    r"\b(?:esta secci[oó]n debe|la secci[oó]n debe|la lectura debe|debe limitarse|"
    r"deben rotularse|no se debe inferir|requiere conservarse|sin completar el dato|"
    r"los datos suministrados|informaci[oó]n disponible permite comunicar|"
    r"no debe(?:n)?\s+(?:presentarse|interpretarse|comunicarse)|"
    r"debe(?:n)?\s+(?:permanecer|conservar|rotular|limitar|interpretar|comunicar(?:se)?|mostrar)|"
    r"el plan de acci[oó]n debe|la base disponible permite estructurar|la comunicaci[oó]n final debe)\b",
    re.IGNORECASE,
)
_REDACTION_MARKER = re.compile(r"\[(?:PHONE|EMAIL|DOCUMENT_ID|PRIVATE_URL|SECRET)\]")


def _client_copy(value: str) -> str:
    """Remove model-facing instructions and broken privacy markers from final copy."""
    kept = []
    for block in re.split(r"(?<=[.!?])\s+|\n+", value or ""):
        text = block.strip()
        if text and not _INTERNAL_COPY.search(text) and not _REDACTION_MARKER.search(text):
            kept.append(text)
    return "\n".join(kept)


def _unique_claims(claims, seen: set[str] | None = None, narrative: str = ""):
    seen = seen if seen is not None else set()
    narrative_key = _normalized_text(narrative)
    unique = []
    for claim in claims:
        key = _normalized_text(claim.text)
        if not key or key in seen or (narrative_key and key in narrative_key):
            continue
        seen.add(key)
        unique.append(claim)
    return unique


def _visual_state(config: dict, section_key: str) -> dict:
    return dict((config.get("section_visuals") or {}).get(section_key) or {})


def proposal_diff(report, proposal: ReportAIAssistantProposal) -> list[dict]:
    changes = []
    config = dict(report.editorial_config or {})
    current_preset = (config.get("visual_config") or {}).get("preset", "AUTO")
    if current_preset != proposal.recommended_preset:
        changes.append({"type": "preset", "key": "preset", "current": current_preset, "proposed": proposal.recommended_preset})
    if config.get("target_page_count") != proposal.estimated_pages:
        changes.append({"type": "target_pages", "key": "report", "current": config.get("target_page_count"), "proposed": proposal.estimated_pages})
    by_key = {section.section_key: section for section in report.sections}
    page_overrides = config.get("page_overrides") or {}
    seen_findings: set[str] = set()
    for item in proposal.sections:
        current = by_key[item.section_key]
        visual = _visual_state(config, item.section_key)
        comparisons = (
            ("visibility", current.is_enabled, item.visible),
            ("order", current.sort_order, item.order),
            ("premium_variant", visual.get("premium_variant", "AUTO"), item.premium_variant),
            ("emphasis", visual.get("emphasis", "NORMAL"), item.emphasis),
            ("selected_metrics", visual.get("selected_metric_keys", []), item.selected_metric_keys),
            ("page_mode", (page_overrides.get(item.section_key) or {}).get("mode", "AUTO"), item.page_mode),
            ("selected_evidence", [], [str(value) for value in item.selected_evidence_ids]),
        )
        for change_type, old, new in comparisons:
            if old != new:
                changes.append({"type": change_type, "key": item.section_key, "current": old, "proposed": new})
        proposed_text = _section_narrative(item, seen_findings)
        if proposed_text is not None and proposed_text != (current.content or {}).get("text"):
            changes.append({"type": "narrative", "key": item.section_key, "current": (current.content or {}).get("text"), "proposed": proposed_text})
    for kind, values in (("executive_summary", proposal.executive_summary), ("key_findings", proposal.key_findings), ("recommendations", proposal.recommendations), ("conclusion", proposal.conclusion)):
        if values:
            changes.append({"type": kind, "key": kind, "current": None, "proposed": len(values)})
    return changes


def _section_narrative(item, seen_findings: set[str] | None = None) -> str | None:
    parts = []
    narrative = _client_copy(item.narrative.strip()) if item.narrative else ""
    if narrative:
        parts.append(narrative)
    safe_findings = [claim for claim in item.findings if _client_copy(claim.text)]
    findings = _unique_claims(safe_findings, seen_findings, narrative)
    if findings:
        title = SECTION_FINDING_TITLES.get(item.section_key, "Aspectos relevantes")
        parts.append(f"{title}:\n{_claim_text(findings)}")
    return "\n\n".join(parts) or None


def _set_generated_text(section, text: str | None, generation_id: UUID) -> None:
    if not text:
        return
    content = dict(section.content or {})
    had_text = bool(content.get("text"))
    content.update({"text": text, "text_origin": "ENRICHED" if had_text else "GENERATED", "ai_generation_id": str(generation_id)})
    section.content = content


def _apply_global_content(by_key: dict, accepted: set[str], proposal, generation_id: UUID) -> None:
    summary = by_key.get("executive_summary")
    if summary and summary.section_key in accepted:
        parts = []
        summary_claims = _unique_claims(proposal.executive_summary)
        if summary_claims:
            parts.append(_claim_text(summary_claims))
        key_findings = _unique_claims(proposal.key_findings, {_normalized_text(item.text) for item in summary_claims})
        if key_findings:
            parts.append("Hallazgos clave:\n" + _claim_text(key_findings))
        _set_generated_text(summary, "\n\n".join(parts) or None, generation_id)

    recommendations = by_key.get("recommendations")
    if recommendations and recommendations.section_key in accepted and proposal.recommendations:
        content = dict(recommendations.content or {})
        existing = [item for item in content.get("items") or [] if not item.get("_ai_generated")]
        generated = [{
            "label": item.title, "description": item.description, "priority": item.priority,
            "source_keys": ",".join(item.source_keys), "origin": item.origin,
            "_ai_generated": True, "_ai_kind": "recommendation", "_is_visible": True,
        } for item in proposal.recommendations]
        content.update({"items": [*existing, *generated], "ai_generation_id": str(generation_id)})
        recommendations.content = content

    conclusion = by_key.get("conclusion")
    if conclusion and conclusion.section_key in accepted:
        _set_generated_text(conclusion, _claim_text(proposal.conclusion) or None, generation_id)


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
    unknown = accepted.difference(by_key)
    if unknown:
        raise HTTPException(422, f"Unknown report sections: {', '.join(sorted(unknown))}")

    config = dict(report.editorial_config or {})
    visual = dict(config.get("visual_config") or {})
    section_visuals = dict(config.get("section_visuals") or {})
    page_overrides = dict(config.get("page_overrides") or {})
    if apply_preset:
        visual["preset"] = proposal.recommended_preset
        config["target_page_count"] = proposal.estimated_pages
    config["mode"] = "CUSTOM"

    proposed_by_key = {item.section_key: item for item in proposal.sections}
    for key in accepted:
        item = proposed_by_key.get(key)
        if not item:
            continue
        section_visual = dict(section_visuals.get(key) or {})
        section_visual.update({
            "premium_variant": item.premium_variant,
            "emphasis": item.emphasis,
            "selected_metric_keys": list(item.selected_metric_keys),
        })
        section_visuals[key] = section_visual
        if item.page_mode == "AUTO":
            page_overrides.pop(key, None)
        else:
            page_overrides[key] = {"mode": item.page_mode, "group_with": item.group_with}

    config.update({"visual_config": visual, "section_visuals": section_visuals, "page_overrides": page_overrides})
    report.editorial_config = config

    original_order = {section.section_key: section.sort_order for section in report.sections}
    seen_findings: set[str] = set()
    for item in proposal.sections:
        if item.section_key not in accepted:
            continue
        section = by_key[item.section_key]
        section.is_enabled = item.visible
        _set_generated_text(section, _section_narrative(item, seen_findings), generation.id)
        section.updated_at = datetime.now(UTC).replace(tzinfo=None)
    ordered = sorted(report.sections, key=lambda section: (
        proposed_by_key[section.section_key].order if section.section_key in accepted and section.section_key in proposed_by_key else original_order[section.section_key],
        original_order[section.section_key],
    ))
    for index, section in enumerate(ordered):
        section.sort_order = index

    _apply_global_content(by_key, accepted, proposal, generation.id)

    evidence_targets = {str(evidence_id): item.section_key for item in proposal.sections if item.section_key in accepted for evidence_id in item.selected_evidence_ids}
    evidence_targets.update({str(item.evidence_id): item.section_key for item in proposal.evidence_suggestions if item.section_key in accepted})
    per_section_order: dict[str, int] = {}
    for evidence in report.evidences:
        target = evidence_targets.get(str(evidence.evidence_id))
        if target:
            evidence.section_id = by_key[target].id
            evidence.is_enabled = True
            evidence.sort_order = per_section_order.get(target, 0)
            per_section_order[target] = evidence.sort_order + 1

    visual_audit = report_visual_audit_service.audit_correct_and_verify(report, accepted)
    generation.applied = True
    report.edit_version += 1
    report.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return revision, report_builder_service.get_editor(db, report.id, user), visual_audit
