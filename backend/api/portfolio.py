import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import PortfolioHistoryPoint, PortfolioSummary
from services.portfolio import PortfolioService
from services.portfolio_history import PortfolioHistoryService

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
