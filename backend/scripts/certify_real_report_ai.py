"""Run the four explicitly authorized real report-AI certification cases, once each."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.core import Report, ReportScope, User
from app.services.ai.ai_service import AIService
from app.services.ai.schemas import ReportAIAssistantRequest, ReportAIRequest


async def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.is_active.is_(True)).order_by(User.created_at))
        event_id = db.scalar(
            select(Report.event_id).where(Report.scope == ReportScope.SHOW)
            .group_by(Report.event_id).having(func.count(Report.id) >= 2).limit(1)
        )
        report = db.scalar(select(Report).where(
            Report.scope == ReportScope.EVENT,
            Report.event_id == event_id if event_id else Report.event_id.is_not(None),
        ).order_by(Report.updated_at.desc()).limit(1))
        if not user or not report:
            raise SystemExit("No local user/report is available for real certification")
        sections = {section.section_key: section for section in report.sections}
        waste = sections.get("waste")
        executive = sections.get("executive_summary")
        if not waste or not executive:
            raise SystemExit("Selected report does not contain waste and executive_summary")
        service = AIService()
        cases = [
            ("waste_narrative", service.generate_report_section_draft(db, report.id, waste.id, user, ReportAIRequest(operation="REGENERATE", style="TECHNICAL", length="SHORT"))),
            ("executive_summary", service.generate_report_section_draft(db, report.id, executive.id, user, ReportAIRequest(operation="REGENERATE", style="EXECUTIVE", length="SHORT"))),
            ("multishow_comparison", service.generate_report_assistant_proposal(db, report.id, user, ReportAIAssistantRequest(instructions="Compara los shows usando exclusivamente las comparaciones calculadas por backend y destaca diferencias verificables.", force_refresh=True))),
            ("complete_proposal", service.generate_report_assistant_proposal(db, report.id, user, ReportAIAssistantRequest(instructions="Crea una propuesta premium completa, grounded y profesional con todas las secciones disponibles, sin inventar datos.", force_refresh=True))),
        ]
        for name, call in cases:
            try:
                result = await call
                print(json.dumps({"case": name, "status": "SUCCEEDED", "generation_id": str(result.generation_id), "model": result.effective_model or result.model, "input_tokens": result.input_tokens, "output_tokens": result.output_tokens, "cached_input_tokens": result.cached_input_tokens, "actual_cost_usd": result.actual_cost_usd}, ensure_ascii=False))
            except Exception as exc:
                print(json.dumps({"case": name, "status": "FAILED", "error_type": type(exc).__name__, "error_code": getattr(exc, "code", None), "message": str(exc)[:500]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
