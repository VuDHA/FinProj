import datetime
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import get_session
from schemas import CompareCorrelation, CompareMetrics
from services.compare import CompareService

router = APIRouter(prefix="/compare", tags=["compare"])

MAX_COMPARE_SYMBOLS = 8


def _parse_symbols(symbols: str, types: str) -> List[Tuple[str, str]]:
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        raise HTTPException(status_code=400, detail="symbols is required")
    if len(syms) > MAX_COMPARE_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_COMPARE_SYMBOLS} symbols allowed",
        )

    if types:
        tys = [t.strip().upper() for t in types.split(",") if t.strip()]
    else:
        tys = ["STOCK"] * len(syms)

    if len(tys) != len(syms):
        raise HTTPException(
            status_code=400, detail="symbols and types must have the same length"
        )

    valid_types = {"STOCK", "FUND"}
    for t in tys:
        if t not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported type: {t}. Must be STOCK or FUND",
            )

    return list(zip(syms, tys))


@router.get("/metrics", response_model=List[CompareMetrics])
def get_metrics(
    symbols: str,
    start: datetime.date,
    end: datetime.date,
    types: str = "",
    session: Session = Depends(get_session),
):
    pairs = _parse_symbols(symbols, types)
    if start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")
    return CompareService(session).metrics(pairs, start, end)


@router.get("/correlation", response_model=CompareCorrelation)
def get_correlation(
    symbols: str,
    start: datetime.date,
    end: datetime.date,
    types: str = "",
    session: Session = Depends(get_session),
):
    pairs = _parse_symbols(symbols, types)
    if start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")
    return CompareService(session).correlation(pairs, start, end)
