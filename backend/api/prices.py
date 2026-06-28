import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import Asset, PriceSnapshot
from schemas import BenchmarkPoint, FundDetail, MarketSymbol, PriceHistoryPoint, PriceSnapshotRead, Quote
from services.market_data import MarketDataService

router = APIRouter(prefix="/prices", tags=["prices"])

DEFAULT_WATCHLIST = [
    "VCB", "VHM", "VIC", "FPT", "GAS", "HPG", "MBB", "MSN", "MWG",
    "PLX", "SSI", "TCB", "VIB", "VPB", "E1VFVN30", "FUEVFVND", "FUESSVFL",
]


def _get_or_create_snapshot(session: Session, asset: Asset, data: dict) -> PriceSnapshot | None:
    """Persist a price snapshot if it is valid and not already stored for this date."""
    if not data or not data.get("price"):
        return None

    date = data.get("date")
    if not date:
        return None

    existing = session.exec(
        select(PriceSnapshot).where(
            PriceSnapshot.asset_id == asset.id,
            PriceSnapshot.date == date,
        )
    ).first()
    if existing:
        return existing

    snapshot = PriceSnapshot(
        asset_id=asset.id,
        date=date,
        price=data["price"],
        change=data.get("change"),
        change_percent=data.get("change_percent"),
    )
    session.add(snapshot)
    return snapshot


@router.post("/refresh-all")
def refresh_all_prices(session: Session = Depends(get_session)):
    service = MarketDataService()
    assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
    updated = 0
    failed = 0
    for asset in assets:
        data = service.fetch_price(asset)
        if _get_or_create_snapshot(session, asset, data):
            updated += 1
        else:
            failed += 1
    session.commit()
    return {"updated": updated, "failed": failed, "date": datetime.date.today().isoformat()}


@router.post("/refresh/{asset_id}")
def refresh_price(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    service = MarketDataService()
    data = service.fetch_price(asset)
    if not data:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")

    snapshot = _get_or_create_snapshot(session, asset, data)
    if not snapshot:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")

    session.commit()
    session.refresh(snapshot)
    return snapshot


@router.get("/history/{asset_id}", response_model=List[PriceHistoryPoint])
def get_price_history(
    asset_id: int,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    service = MarketDataService()
    history = service.fetch_history(asset.symbol, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


@router.get("/quote", response_model=List[Quote])
def get_quotes(symbols: str = ",".join(DEFAULT_WATCHLIST)):
    service = MarketDataService()
    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    return service.fetch_quotes(symbols_list)


@router.get("/symbols", response_model=List[MarketSymbol])
def get_all_symbols():
    service = MarketDataService()
    return service.fetch_all_symbols()


@router.get("/stocks", response_model=List[MarketSymbol])
def get_all_stocks():
    service = MarketDataService()
    return service.fetch_all_stocks()


@router.get("/funds", response_model=List[MarketSymbol])
def get_all_funds():
    service = MarketDataService()
    return service.fetch_all_funds()


@router.get("/fund-detail/{symbol}", response_model=FundDetail)
def get_fund_detail(symbol: str):
    service = MarketDataService()
    data = service.fetch_fund_detail(symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Fund not found")
    return data


@router.get("/market-history/{symbol}", response_model=List[PriceHistoryPoint])
def get_market_history(
    symbol: str,
    type: str,
    start: datetime.date,
    end: datetime.date,
):
    service = MarketDataService()
    history = service.fetch_market_history(symbol, type, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch market history")
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


class BenchmarkPricePoint(BaseModel):
    date: datetime.date
    price: float


@router.get("/benchmark/{symbol}", response_model=List[BenchmarkPoint])
def get_benchmark(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    from services.benchmark import BenchmarkService

    data = BenchmarkService(session).get_comparison(symbol, start, end)
    if not data:
        raise HTTPException(status_code=502, detail="Failed to fetch benchmark data")
    return data


@router.get("/benchmark-raw/{symbol}", response_model=List[BenchmarkPricePoint])
def get_benchmark_raw(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
):
    service = MarketDataService()
    history = service.fetch_benchmark_history(symbol, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch benchmark data")
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


@router.get("/{asset_id}", response_model=List[PriceSnapshotRead])
def get_prices(asset_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.asset_id == asset_id)
        .order_by(PriceSnapshot.date.desc())
    ).all()
