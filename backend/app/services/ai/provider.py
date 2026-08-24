from app.core.config import Settings
from app.services.ai.ai_router import build_provider


def report_provider(settings: Settings):
    return build_provider(settings)
