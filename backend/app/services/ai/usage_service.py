from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, select
from app.models.ai import AIGeneration
from app.services.ai.pricing import PricingRegistry


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


def report_monthly_spend(db) -> Decimal:
    start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    value = db.scalar(
        select(func.coalesce(func.sum(AIGeneration.actual_cost_usd), 0)).where(
            AIGeneration.created_at >= start,
            AIGeneration.capability.like("reports.%"),
            AIGeneration.status == "SUCCEEDED",
        )
    )
    return Decimal(str(value or 0))


def estimate_report_cost(settings, estimated_input_tokens: int = 8000) -> Decimal:
    pricing = PricingRegistry(getattr(settings, "ai_report_pricing_json", None)).get(
        getattr(settings, "ai_report_provider", settings.ai_provider), getattr(settings, "ai_report_model", None) or settings.ai_model
    )
    if not pricing:
        return Decimal("0")
    return pricing.cost(estimated_input_tokens, getattr(settings, "ai_report_max_output_tokens", settings.ai_max_output_tokens))


def enforce_report_budget(db, settings) -> Decimal:
    estimate = estimate_report_cost(settings)
    if report_monthly_spend(db) + estimate > Decimal(str(getattr(settings, "ai_report_monthly_budget_usd", getattr(settings, "ai_monthly_budget_usd", 10)))):
        raise RuntimeError("REPORT_AI_BUDGET_EXCEEDED")
    return estimate


def actual_report_cost(settings, result) -> Decimal | None:
    pricing = PricingRegistry(getattr(settings, "ai_report_pricing_json", None)).get(
        getattr(settings, "ai_report_provider", settings.ai_provider), result.effective_model or getattr(settings, "ai_report_model", None) or settings.ai_model
    )
    return pricing.cost(result.input_tokens, result.output_tokens, result.cached_input_tokens) if pricing else None


def mark_stale_pending(db, settings) -> int:
    threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=getattr(settings, "ai_report_pending_stale_minutes", 15))
    rows = list(db.scalars(select(AIGeneration).where(
        AIGeneration.capability.like("reports.%"),
        AIGeneration.status == "PENDING",
        AIGeneration.created_at < threshold,
    )).all())
    for row in rows:
        row.status = "STALE"
        row.error_code = "stale_pending"
        row.error_message = "Generation exceeded the configured pending lifetime"
        row.completed_at = datetime.now(UTC).replace(tzinfo=None)
    if rows:
        db.commit()
    return len(rows)
