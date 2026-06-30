from fastapi import APIRouter

from services.ai_queue import AIQueue

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    """Return the current state of the global AI queue."""
    return AIQueue().status()
