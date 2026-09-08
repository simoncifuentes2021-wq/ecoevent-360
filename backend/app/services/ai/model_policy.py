"""Central model policy for report AI capabilities with safe legacy fallbacks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportModelPolicy:
    model: str
    max_output_tokens: int
    tier: str


FAST_CAPABILITIES = {"reports.section_draft"}
EDITORIAL_CAPABILITIES = {"reports.editorial_plan", "reports.premium_assistant"}


def resolve_report_model(settings, capability: str) -> ReportModelPolicy:
    fallback = getattr(settings, "ai_report_model", None) or settings.ai_model
    configured_max = getattr(settings, "ai_report_max_output_tokens", settings.ai_max_output_tokens)
    if capability in FAST_CAPABILITIES:
        return ReportModelPolicy(
            getattr(settings, "ai_report_fast_model", None) or fallback,
            min(configured_max, getattr(settings, "ai_report_fast_max_output_tokens", 1800)),
            "FAST",
        )
    if capability in EDITORIAL_CAPABILITIES:
        return ReportModelPolicy(
            getattr(settings, "ai_report_editorial_model", None) or fallback,
            max(configured_max, getattr(settings, "ai_report_editorial_max_output_tokens", 4000)),
            "EDITORIAL",
        )
    return ReportModelPolicy(fallback, configured_max, "DEFAULT")


def visual_audit_model(settings) -> str | None:
    """Optional future semantic judge; deterministic Chromium audit remains primary and free."""
    return getattr(settings, "ai_report_audit_model", None)
