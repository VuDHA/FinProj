from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import BacktestRequest, BacktestResult
from services.backtest import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/", response_model=BacktestResult)
def run_backtest(request: BacktestRequest, session: Session = Depends(get_session)):
    return BacktestService(session).run(request)
