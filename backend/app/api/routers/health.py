from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def api_health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}

