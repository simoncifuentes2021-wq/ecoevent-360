import re
from pydantic import BaseModel, Field
from app.services.ai.report_layout_service import AIPagePlanSchema, LayoutValidator
from app.services.report_data_binding_registry import catalog


class GroundedClaim(BaseModel):
    text: str = Field(max_length=2000)
    sources: list[str] = Field(min_length=1, max_length=20)


class AIFullReportPlan(BaseModel):
    title: str = Field(max_length=180)
    pages: list[AIPagePlanSchema] = Field(min_length=1, max_length=12)
    claims: list[GroundedClaim] = Field(default_factory=list, max_length=100)
    excluded_topics: list[str] = Field(default_factory=list, max_length=30)


def get_event_overview(report):
    return {item["key"]: item for item in catalog(report) if item["key"].startswith("event.")}


def get_show_overview(report):
    return {item["key"]: item for item in catalog(report) if item["key"].startswith("show.")}


def get_services_summary(report):
    section = next((item for item in report.sections if item.section_key == "services"), None)
    if not section:
        return {}
    content = section.content or {}
    return {
        "services.fields": [item for item in content.get("fields", []) if item.get("is_visible", True)],
        "services.items": [item for item in content.get("items", []) if item.get("_is_visible", True)],
    }


def get_bike_zone_summary(report):
    return _domain(report, "bike_zone.")


def get_waste_summary(report):
    return _domain(report, "waste.")


def get_carbon_summary(report):
    return _domain(report, "carbon.")


def get_environmental_impact(report):
    return _domain(report, "environmental_impact.")


def get_forms_summary(report):
    return _domain(report, "forms.")


def get_incidents_summary(report):
    return _domain(report, "incidents.")


def get_tasks_summary(report):
    return _domain(report, "tasks.")


def _domain(report, prefix):
    return {item["key"]: item for item in catalog(report) if item["key"].startswith(prefix)}


def get_available_evidences(report):
    return [
        {
            "id": str(item.evidence_id),
            "caption": item.caption or item.evidence.description,
            "session_id": str(item.evidence.session_id) if item.evidence.session_id else None,
        }
        for item in report.evidences
        if item.is_enabled
    ]


def get_show_comparison(reports):
    return [
        {
            "show": report.session.name if report.session else None,
            "metrics": {
                item["key"]: item["value"]
                for item in catalog(report)
                if item["availability"] == "AVAILABLE"
            },
        }
        for report in reports
    ]


class ReportAIValidator:
    @staticmethod
    def validate(
        raw: dict, grounded_values: dict, allowed_evidence_ids: set[str] | None = None
    ) -> AIFullReportPlan:
        plan = AIFullReportPlan.model_validate(raw)
        for page in plan.pages:
            LayoutValidator.validate(page.model_dump())
            for element in page.elements:
                evidence_id = element.content.get("evidence_id")
                if evidence_id and evidence_id not in (allowed_evidence_ids or set()):
                    raise ValueError("AI selected a forbidden evidence")
        for claim in plan.claims:
            if any(source not in grounded_values for source in claim.sources):
                raise ValueError("AI claim has an unknown source")
            allowed = {
                str(grounded_values[source]).replace(".", ",") for source in claim.sources
            } | {str(grounded_values[source]) for source in claim.sources}
            numbers = re.findall(r"-?\d+(?:[.,]\d+)?", claim.text)
            if any(number not in allowed for number in numbers):
                raise ValueError("AI claim introduced an ungrounded number")
        return plan
