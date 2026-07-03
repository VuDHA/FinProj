import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import PortfolioAIInsightResponse, PortfolioHistoryPoint, PortfolioSummary
from .ai_utils import handle_ai_insight_error
from services.ai_insights import PortfolioInsightService
from services.portfolio import PortfolioService
from services.portfolio_history import PortfolioHistoryService
from services.rebalance import RebalanceService
from services.risk_metrics import RiskMetricsService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/", response_model=PortfolioSummary)
def get_portfolio(session: Session = Depends(get_session)):
    return PortfolioService(session).get_portfolio()


@router.get("/history", response_model=List[PortfolioHistoryPoint])
def get_portfolio_history(
    start: Optional[datetime.date] = None,
    end: Optional[datetime.date] = None,
    session: Session = Depends(get_session),
):
    return PortfolioHistoryService(session).get_history(start, end)


@router.post("/ai-insight", response_model=PortfolioAIInsightResponse)
@handle_ai_insight_error
def get_portfolio_ai_insight(session: Session = Depends(get_session)):
    portfolio = PortfolioService(session).get_portfolio()
    risk = RiskMetricsService(session).get_metrics()
    rebalance = RebalanceService(session).suggest()
    return PortfolioInsightService().generate(
        portfolio.model_dump(),
        risk.model_dump(),
        rebalance.model_dump(),
    )
