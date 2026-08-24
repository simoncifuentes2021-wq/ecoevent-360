"""Report narrative facade preserving candidate accept/discard semantics."""

from app.services.ai.ai_service import AIService


class ReportTextService:
    def __init__(self, ai: AIService | None = None):
        self.ai = ai or AIService()

    async def propose(self, db, report_id, section_id, user, options):
        return await self.ai.generate_report_section_draft(db, report_id, section_id, user, options)
