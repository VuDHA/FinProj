from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import get_session
from schemas import (
    BacktestPromptRequest,
    BacktestPromptResponse,
    BacktestRequest,
    BacktestResult,
    BacktestStressRequest,
    BacktestStressResponse,
)
from .ai_utils import handle_ai_insight_error
from services.backtest import BacktestService
from services.prompt_parser import PromptParserError

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/", response_model=BacktestResult)
def run_backtest(request: BacktestRequest, session: Session = Depends(get_session)):
    return BacktestService(session).run(request)


@router.post("/ai", response_model=BacktestPromptResponse)
@handle_ai_insight_error
def run_backtest_from_prompt(
    payload: BacktestPromptRequest, session: Session = Depends(get_session)
):
    try:
        return BacktestService(session).run_from_prompt(payload.prompt)
    except PromptParserError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ai-stress", response_model=BacktestStressResponse)
@handle_ai_insight_error
def run_backtest_stress_from_prompt(
    payload: BacktestStressRequest, session: Session = Depends(get_session)
):
    try:
        return BacktestService(session).run_stress_from_prompt(
            payload.prompt,
            payload.base_request if payload.base_request else BacktestRequest(),
        )
    except PromptParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
