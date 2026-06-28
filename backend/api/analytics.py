from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import AnalyticsSummary
from services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsSummary)
def get_analytics(session: Session = Depends(get_session)):
    return AnalyticsService(session).get_summary()
