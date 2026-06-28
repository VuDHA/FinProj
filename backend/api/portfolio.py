from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import PortfolioSummary
from services.portfolio import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/", response_model=PortfolioSummary)
def get_portfolio(session: Session = Depends(get_session)):
    return PortfolioService(session).get_portfolio()
