from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import ReportSection, User
from app.services import report_builder_service
from app.services.ai.schemas import ReportAIRequest

CAPABILITY = "reports.section_draft"
SENSITIVE_KEYS = {"email", "phone", "telephone", "contact", "address", "rut", "dni", "password", "token", "full_name", "first_name", "last_name", "participant", "responder", "user_id"}


def _safe(value):
    if isinstance(value, dict):
        return {key: _safe(child) for key, child in value.items() if not any(token in key.lower() for token in SENSITIVE_KEYS)}
    if isinstance(value, list):
        return [_safe(child) for child in value]
    return value


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
