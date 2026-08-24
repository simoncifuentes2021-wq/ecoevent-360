from datetime import datetime
from sqlalchemy import func, select
from app.models.ai import AIGeneration


def monthly_generation_count(db) -> int:
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count())
            .select_from(AIGeneration)
            .where(AIGeneration.created_at >= start, AIGeneration.status == "SUCCEEDED")
        )
        or 0
    )


def ensure_budget(settings, estimated_cost_usd: float, spent_usd: float = 0) -> None:
    if spent_usd + estimated_cost_usd > settings.ai_monthly_budget_usd:
        raise RuntimeError("AI monthly budget reached")
