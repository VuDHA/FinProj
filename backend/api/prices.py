import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Asset, PriceSnapshot
from schemas import MarketSymbol, PriceHistoryPoint, PriceSnapshotRead, Quote
from services.market_data import MarketDataService

router = APIRouter(prefix="/prices", tags=["prices"])

DEFAULT_WATCHLIST = [
    "VCB", "VHM", "VIC", "FPT", "GAS", "HPG", "MBB", "MSN", "MWG",
    "PLX", "SSI", "TCB", "VIB", "VPB", "E1VFVN30", "FUEVFVND", "FUESSVFL",
]


@router.post("/refresh-all")
def refresh_all_prices(session: Session = Depends(get_session)):
    service = MarketDataService()
    assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
    updated = 0
    failed = 0
    for asset in assets:
        data = service.fetch_price(asset)
        if data:
            snapshot = PriceSnapshot(asset_id=asset.id, **data)
            session.add(snapshot)
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

    snapshot = PriceSnapshot(asset_id=asset.id, **data)
    session.add(snapshot)
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


@router.get("/{asset_id}", response_model=List[PriceSnapshotRead])
def get_prices(asset_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.asset_id == asset_id)
        .order_by(PriceSnapshot.date.desc())
    ).all()
