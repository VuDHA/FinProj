from fastapi import APIRouter

from config import settings
from services.ai_queue import AIQueue

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    """Return the current state of the global AI queue and provider buckets."""
    status = AIQueue().status()
    status["gemini_configured"] = bool(settings.GEMINI_API_KEY)
    status["ai_provider"] = settings.AI_PROVIDER
    return status


@router.get("/rate-limit")
def ai_rate_limit():
    """Return the current rate-limit status for all AI providers."""
    return AIQueue().status()["providers"]
