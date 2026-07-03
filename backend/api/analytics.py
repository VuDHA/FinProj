import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from database import get_session
from schemas import AnalyticsSummary, RiskMetrics
from services.analytics import AnalyticsService
from services.risk_metrics import RiskMetricsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_model=AnalyticsSummary)
def get_analytics(
    filter_type: Literal["month", "quarter", "year", "custom"] = Query("month"),
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    session: Session = Depends(get_session),
):
    return AnalyticsService(session).get_summary(filter_type, start_date, end_date)


@router.get("/risk", response_model=RiskMetrics)
def get_risk_metrics(session: Session = Depends(get_session)):
    return RiskMetricsService(session).get_metrics()
