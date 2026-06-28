from fastapi import APIRouter

from schemas import GoldFxResponse
from services.gold_fx import get_gold_fx

router = APIRouter(prefix="/gold-fx", tags=["gold-fx"])


@router.get("/", response_model=GoldFxResponse)
def gold_fx():
    return get_gold_fx()
