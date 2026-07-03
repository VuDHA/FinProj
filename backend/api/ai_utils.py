"""Shared utilities for AI insight endpoints."""

from fastapi import HTTPException

from services.ai.ai_insights.prompts import InsightGenerationError
from services.ai.ai_queue import AIQueueBusyError


def handle_ai_insight_error(fn):
    """Decorator that converts AI errors into HTTPException responses.

    - AIQueueBusyError -> 429 with cooldown_seconds
    - InsightGenerationError -> 503
    - HTTPException is re-raised as-is (e.g. 400 from prompt parsing)
    - Unknown exceptions -> 500
    """
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AIQueueBusyError as e:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": str(e),
                    "cooldown_seconds": int(e.cooldown_seconds) + 1,
                },
            ) from e
        except InsightGenerationError as e:
            raise HTTPException(
                status_code=503,
                detail={"message": str(e)},
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail={"message": f"Lỗi khi tạo phân tích AI: {e}"},
            ) from e

    return wrapper
