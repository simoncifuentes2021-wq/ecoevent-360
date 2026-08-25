from app.core.config import Settings
from app.services.ai.providers.base import AIProvider, AIProviderError
from app.services.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.services.ai.providers.openrouter import OpenRouterProvider
from app.services.ai.providers.openai_responses import OpenAIResponsesProvider


def build_provider(settings: Settings) -> AIProvider:
    if not settings.ai_api_key:
        raise AIProviderError("not_configured", "AI provider credentials are not configured")
    provider = settings.ai_provider.strip().lower()
    if provider == "openrouter":
        return OpenRouterProvider(
            settings.ai_api_key,
            settings.ai_base_url or "https://openrouter.ai/api/v1",
            settings.ai_timeout_seconds,
        )
    if provider == "openai":
        return OpenAICompatibleProvider(
            settings.ai_api_key,
            settings.ai_base_url or "https://api.openai.com/v1",
            settings.ai_timeout_seconds,
        )
    raise AIProviderError("unsupported_provider", f"Unsupported AI provider: {provider}")


def build_report_provider(settings: Settings) -> AIProvider:
    provider = settings.ai_report_provider.strip().lower()
    api_key = settings.ai_report_api_key or settings.openai_api_key
    if not api_key:
        raise AIProviderError("not_configured", "Report AI provider credentials are not configured")
    if provider == "openai":
        return OpenAIResponsesProvider(
            api_key,
            settings.ai_report_base_url or "https://api.openai.com/v1",
            settings.ai_report_timeout_seconds,
        )
    if provider == "openrouter":
        return OpenRouterProvider(
            api_key,
            settings.ai_report_base_url or "https://openrouter.ai/api/v1",
            settings.ai_report_timeout_seconds,
        )
    raise AIProviderError("unsupported_provider", f"Unsupported report AI provider: {provider}")
