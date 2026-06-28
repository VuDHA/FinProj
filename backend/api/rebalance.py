from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from schemas import RebalanceResult
from services.rebalance import RebalanceService

router = APIRouter(prefix="/rebalance", tags=["rebalance"])


@router.get("/", response_model=RebalanceResult)
def get_rebalance_suggestions(session: Session = Depends(get_session)):
    return RebalanceService(session).suggest()
