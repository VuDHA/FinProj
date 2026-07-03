from fastapi import APIRouter, Depends
from sqlmodel import Session

from common.database import get_session
from common.schemas import RebalanceAIInsightResponse, RebalanceResult
from .ai_utils import handle_ai_insight_error
from services.ai.ai_insights import RebalanceInsightService
from services.portfolio.rebalance import RebalanceService

router = APIRouter(prefix="/rebalance", tags=["rebalance"])


@router.get("/", response_model=RebalanceResult)
def get_rebalance_suggestions(session: Session = Depends(get_session)):
    return RebalanceService(session).suggest()


@router.post("/ai-insight", response_model=RebalanceAIInsightResponse)
@handle_ai_insight_error
def get_rebalance_ai_insight(session: Session = Depends(get_session)):
    rebalance = RebalanceService(session).suggest()
    return RebalanceInsightService().generate(rebalance.model_dump())
