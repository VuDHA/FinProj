from fastapi import APIRouter

from services.ai_queue import AIQueue

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    """Return the current state of the global AI queue and provider buckets."""
    return AIQueue().status()


@router.get("/rate-limit")
def ai_rate_limit():
    """Return the current rate-limit status for all AI providers."""
    return AIQueue().status()["providers"]
