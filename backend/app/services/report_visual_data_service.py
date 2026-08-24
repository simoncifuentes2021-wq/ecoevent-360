from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Evidence, Report
from app.models.enums import ReportScope

CHART_TYPES = {"BAR", "DONUT", "LINE", "COMPARISON"}


def validate_evidence(db: Session, report: Report, evidence_id: UUID) -> Evidence:
    evidence = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.event_id == report.event_id)
    )
    if not evidence or (
        report.scope == ReportScope.SHOW and evidence.session_id != report.session_id
    ):
        raise HTTPException(422, "Evidence is outside the report scope")
    return evidence


def chart_dataset(report: Report, section_key: str, chart_type: str) -> dict:
    if chart_type not in CHART_TYPES:
        raise HTTPException(422, "Unsupported chart type")
    section = next((item for item in report.sections if item.section_key == section_key), None)
    if not section:
        return {
            "chart_type": chart_type,
            "labels": [],
            "series": [],
            "availability": "NO_DATA",
            "source": section_key,
        }
    points = []
    for item in (section.content or {}).get("items", [])[:20]:
        value = item.get("value", item.get("weight_kg", item.get("count")))
        if isinstance(value, (int, float)):
            points.append(
                {"label": str(item.get("label", item.get("name", "Dato")))[:80], "value": value}
            )
    if not points:
        for field in (section.content or {}).get("fields", [])[:12]:
            value = field.get("value")
            if isinstance(value, (int, float)):
                points.append(
                    {
                        "label": str(field.get("label", field.get("key", "Dato")))[:80],
                        "value": value,
                        "unit": field.get("unit"),
                    }
                )
    return {
        "chart_type": chart_type,
        "labels": [item["label"] for item in points],
        "series": [{"name": section.title, "data": [item["value"] for item in points]}],
        "points": points,
        "availability": "AVAILABLE" if points else "NO_DATA",
        "source": section_key,
    }
