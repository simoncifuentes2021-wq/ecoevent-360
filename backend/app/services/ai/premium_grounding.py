import re
from decimal import Decimal, InvalidOperation

from app.services.ai.providers.base import AIProviderError
from app.services.ai.schemas import ReportAIAssistantProposal

UNIT_ALIASES = {
    "kg": {"kg"}, "t": {"t", "toneladas"}, "kgCO2e": {"kgco2e", "kg co2e", "kg co₂e"},
    "tCO2e": {"tco2e", "t co2e", "t co₂e"}, "L": {"l", "litros"},
    "kWh": {"kwh"}, "%": {"%", "porcentaje"}, "personas": {"personas", "usuarios", "asistentes"},
}


def _numbers(text: str) -> list[Decimal]:
    values = []
    for raw in re.findall(r"(?<![\w.])-?\d+(?:[.,]\d+)?", text):
        try:
            values.append(Decimal(raw.replace(",", ".")))
        except InvalidOperation:
            pass
    return values


def validate_premium_proposal(proposal: ReportAIAssistantProposal, context: dict) -> None:
    allowed_sections = set(context["allowlists"]["section_keys"])
    allowed_presets = set(context["allowlists"]["presets"])
    allowed_variants = set(context["allowlists"]["premium_variants"])
    sources = context.get("sources") or {}
    evidence_ids = {item["id"] for item in context.get("evidences") or []}
    if str(proposal.report_id) != context["current"]["report_id"]:
        raise AIProviderError("invalid_report", "Proposal targets another report")
    if proposal.recommended_preset not in allowed_presets:
        raise AIProviderError("invalid_preset", "Proposal selected an unknown preset")
    if len({section.section_key for section in proposal.sections}) != len(proposal.sections):
        raise AIProviderError("invalid_section", "Proposal contains duplicate sections")
    for section in proposal.sections:
        if section.section_key not in allowed_sections:
            raise AIProviderError("invalid_section", "Proposal selected an unknown section")
        if section.group_with and (section.group_with not in allowed_sections or section.group_with == section.section_key):
            raise AIProviderError("invalid_group", "Proposal selected an invalid section grouping")
        if section.premium_variant not in allowed_variants:
            raise AIProviderError("invalid_variant", "Proposal selected an unknown premium variant")
        expected_variant = (context["allowlists"].get("variants_by_preset") or {}).get(proposal.recommended_preset, {}).get(section.section_key, "AUTO")
        if section.premium_variant != expected_variant:
            raise AIProviderError("invalid_variant", "Premium variant does not belong to the proposed preset and section")
        if any(str(item) not in evidence_ids for item in section.selected_evidence_ids):
            raise AIProviderError("invalid_evidence", "Proposal selected an unavailable evidence")
        if any(key not in sources for key in section.selected_metric_keys):
            raise AIProviderError("invalid_source", "Proposal selected an unknown metric")
    for suggestion in proposal.evidence_suggestions:
        if str(suggestion.evidence_id) not in evidence_ids or suggestion.section_key not in allowed_sections:
            raise AIProviderError("invalid_evidence", "Proposal selected an unavailable evidence")
    claims = [*proposal.executive_summary, *proposal.key_findings, *proposal.conclusion]
    claims.extend(item for section in proposal.sections for item in section.findings)
    for recommendation in proposal.recommendations:
        claims.append(recommendation)
    for claim in claims:
        if any(key not in sources for key in claim.source_keys):
            raise AIProviderError("invalid_source", "Claim references an unknown source key")
        allowed_numbers = set()
        allowed_units = set()
        for key in claim.source_keys:
            source = sources[key]
            allowed_numbers.update(_numbers(str(source.get("value"))))
            unit = str(source.get("unit") or "")
            allowed_units.update(UNIT_ALIASES.get(unit, {unit.lower()} if unit else set()))
        if any(number not in allowed_numbers for number in _numbers(claim.text if hasattr(claim, "text") else claim.description)):
            raise AIProviderError("unsupported_numeric_claim", "Claim introduced a number not present in its sources")
        rendered = (claim.text if hasattr(claim, "text") else claim.description).lower()
        mentioned_units = {alias for aliases in UNIT_ALIASES.values() for alias in aliases if alias and re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", rendered)}
        if mentioned_units and not mentioned_units.intersection(allowed_units):
            raise AIProviderError("unit_mismatch", "Claim uses a unit not backed by its sources")
