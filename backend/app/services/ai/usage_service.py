from datetime import UTC, datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, select
from app.models.ai import AIGeneration
from app.services.ai.pricing import PricingRegistry
from app.services.ai.providers.base import AIProviderError


def monthly_generation_count(db) -> int:
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count())
            .select_from(AIGeneration)
            .where(AIGeneration.created_at >= start, AIGeneration.status == "SUCCEEDED", AIGeneration.capability.like("reports.%"))
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


def estimate_report_cost(settings, estimated_input_tokens: int = 8000, *, model: str | None = None, max_output_tokens: int | None = None) -> Decimal:
    pricing = PricingRegistry(getattr(settings, "ai_report_pricing_json", None)).get(
        getattr(settings, "ai_report_provider", settings.ai_provider), model or getattr(settings, "ai_report_model", None) or settings.ai_model
    )
    if not pricing:
        raise AIProviderError("REPORT_AI_PRICING_NOT_CONFIGURED", "Report AI pricing is not configured for the selected provider and model")
    return pricing.cost(estimated_input_tokens, max_output_tokens or getattr(settings, "ai_report_max_output_tokens", settings.ai_max_output_tokens))


def enforce_report_budget(db, settings, *, model: str | None = None, max_output_tokens: int | None = None) -> Decimal:
    estimate = estimate_report_cost(settings, model=model, max_output_tokens=max_output_tokens)
    ensure_report_budget(
        report_monthly_spend(db), estimate,
        Decimal(str(getattr(settings, "ai_report_monthly_budget_usd", getattr(settings, "ai_monthly_budget_usd", 10)))),
    )
    return estimate


def ensure_report_budget(spent: Decimal, estimate: Decimal, budget: Decimal) -> None:
    if spent + estimate > budget:
        raise RuntimeError("REPORT_AI_BUDGET_EXCEEDED")


def actual_report_cost(settings, result, *, model: str | None = None) -> Decimal | None:
    pricing = PricingRegistry(getattr(settings, "ai_report_pricing_json", None)).get(
        getattr(settings, "ai_report_provider", settings.ai_provider), result.effective_model or model or getattr(settings, "ai_report_model", None) or settings.ai_model
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
