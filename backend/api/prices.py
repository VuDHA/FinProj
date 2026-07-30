import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models import Asset, PriceSnapshot
from schemas import BenchmarkPoint, FundDetail, MarketAIInsightResponse, MarketSymbol, PriceHistoryPoint, PriceSnapshotRead, Quote, StockDetail, SymbolAIInsightResponse
from .ai_utils import handle_ai_insight_error
from services.ai_insights import MarketInsightService, SymbolAIInsightService
from services.asset_type_config import is_market_price_type
from services.gold_fx import get_gold_fx
from services.market_data import MarketDataService
from services.portfolio import PortfolioService

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
    service = MarketDataService(session)
    assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
    market_assets = [a for a in assets if is_market_price_type(session, a.type)]
    updated = 0
    failed = 0
    warnings: List[str] = []
    for asset in market_assets:
        data, asset_warnings = service.fetch_price_with_warnings(asset)
        warnings.extend(asset_warnings)
        if _get_or_create_snapshot(session, asset, data):
            updated += 1
        else:
            failed += 1
    session.commit()
    try:
        from .alerts import evaluate_notifications

        triggered = evaluate_notifications(session)
        if triggered:
            print(f"[refresh-all] {len(triggered)} price alerts triggered")
    except Exception as e:
        print(f"[refresh-all] alert evaluation error: {e}")

    return {"updated": updated, "failed": failed, "warnings": warnings, "date": datetime.date.today().isoformat(), "skipped": len(assets) - len(market_assets)}


@router.post("/refresh/{asset_id}")
def refresh_price(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    if not is_market_price_type(session, asset.type):
        raise HTTPException(
            status_code=400,
            detail=f"Asset type {asset.type} does not support automatic price refresh",
        )

    service = MarketDataService(session)
    data, warnings = service.fetch_price_with_warnings(asset)
    if not data:
        detail = "Failed to fetch market data"
        if warnings:
            detail += f" ({'; '.join(warnings)})"
        raise HTTPException(status_code=502, detail=detail)

    snapshot = _get_or_create_snapshot(session, asset, data)
    if not snapshot:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")

    session.commit()
    try:
        from .alerts import evaluate_notifications

        triggered = evaluate_notifications(session)
        if triggered:
            print(f"[refresh] {len(triggered)} price alerts triggered")
    except Exception as e:
        print(f"[refresh] alert evaluation error: {e}")

    session.refresh(snapshot)
    return {"snapshot": snapshot, "warnings": warnings}


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

    service = MarketDataService(session)
    history = service.fetch_history(asset.symbol, asset.type, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


@router.get("/quote", response_model=List[Quote])
def get_quotes(
    symbols: str = ",".join(DEFAULT_WATCHLIST),
    asset_type: Optional[str] = None,
    types: Optional[str] = None,
    session: Session = Depends(get_session),
):
    service = MarketDataService(session)
    symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    if asset_type:
        return service.fetch_quotes(symbols_list, asset_type=asset_type)

    # Build an optional per-symbol type map from the query parameter.
    type_map: dict[str, str] = {}
    if types:
        type_list = [t.strip().upper() for t in types.split(",") if t.strip()]
        if len(type_list) == len(symbols_list):
            type_map = dict(zip(symbols_list, type_list))

    # Look up asset types from the database as a fallback.
    assets = session.exec(select(Asset).where(Asset.symbol.in_(symbols_list))).all()
    by_symbol = {a.symbol.upper(): a for a in assets}

    by_type: dict[str, list[str]] = {}
    for symbol in symbols_list:
        type_ = type_map.get(symbol)
        if not type_:
            asset = by_symbol.get(symbol)
            type_ = asset.type if asset else "STOCK"
        by_type.setdefault(type_, []).append(symbol)

    quote_map: dict[str, dict] = {}
    for type_, syms in by_type.items():
        for q in service.fetch_quotes(syms, asset_type=type_):
            quote_map[q["symbol"].upper()] = q

    # Preserve input order.
    return [quote_map[s] for s in symbols_list]


@router.get("/symbols", response_model=List[MarketSymbol])
def get_all_symbols(session: Session = Depends(get_session)):
    service = MarketDataService(session)
    return service.fetch_all_symbols()


@router.get("/stocks", response_model=List[MarketSymbol])
def get_all_stocks(session: Session = Depends(get_session)):
    service = MarketDataService(session)
    return service.fetch_all_stocks()


@router.get("/funds", response_model=List[MarketSymbol])
def get_all_funds(session: Session = Depends(get_session)):
    service = MarketDataService(session)
    return service.fetch_all_funds()


@router.get("/fund-detail/{symbol}", response_model=FundDetail)
def get_fund_detail(symbol: str, session: Session = Depends(get_session)):
    service = MarketDataService(session)
    data = service.fetch_fund_detail(symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Fund not found")
    return data


@router.get("/stock-detail/{symbol}", response_model=StockDetail)
def get_stock_detail(symbol: str, session: Session = Depends(get_session)):
    service = MarketDataService(session)
    data = service.fetch_stock_detail(symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Stock not found")
    return data


@router.get("/symbol-ai-insight/{symbol}", response_model=SymbolAIInsightResponse)
@handle_ai_insight_error
def get_symbol_ai_insight(
    symbol: str,
    type: str,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    service = MarketDataService(session)
    detail = service.fetch_fund_detail(symbol) if type == "FUND" else service.fetch_stock_detail(symbol)
    if not detail:
        raise HTTPException(status_code=404, detail="Symbol not found")

    history_map = service.fetch_market_history_with_backfill(symbol, type, start, end)
    history = [{"date": d.isoformat(), "price": p} for d, p in sorted(history_map.items())]

    # Compute stats compatible with SymbolAIInsightService expectations.
    stats = None
    if history:
        prices = [p for _, p in sorted(history_map.items())]
        first = prices[0]
        last = prices[-1]
        max_price = max(prices)
        min_price = min(prices)
        avg = sum(prices) / len(prices)
        days = len(prices)
        total_return = ((last - first) / first * 100) if first else 0.0
        years = max(days / 252, 1 / 252)
        annualized = ((last / first) ** (1 / years) - 1) * 100 if first else 0.0
        daily_returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        volatility = (
            (sum(r * r for r in daily_returns) / len(daily_returns)) ** 0.5 * (252 ** 0.5) * 100
            if daily_returns
            else 0.0
        )
        stats = {
            "total_return": total_return,
            "annualized_return": annualized,
            "volatility": volatility,
            "max": max_price,
            "min": min_price,
            "avg": avg,
            "days": days,
        }

    return SymbolAIInsightService().generate(
        symbol=detail.get("symbol", symbol),
        name=detail.get("name", symbol),
        symbol_type=type,
        detail=detail,
        history=history,
        stats=stats,
    )


@router.get("/market-history/{symbol}", response_model=List[PriceHistoryPoint])
def get_market_history(
    symbol: str,
    type: str,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    service = MarketDataService(session)
    history = service.fetch_market_history_with_backfill(symbol, type, start, end)
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


@router.post("/market-history/{symbol}/fill")
def fill_market_history(
    symbol: str,
    type: str,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    service = MarketDataService(session)
    history = service.force_backfill_history(symbol, type, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch market history")
    return {
        "symbol": symbol.upper(),
        "type": type,
        "filled": len(history),
        "start": start,
        "end": end,
    }


@router.post("/market-ai-insight", response_model=MarketAIInsightResponse)
@handle_ai_insight_error
def get_market_ai_insight(session: Session = Depends(get_session)):
    service = MarketDataService(session)
    watchlist = service.fetch_quotes(DEFAULT_WATCHLIST)
    portfolio = PortfolioService(session).get_portfolio()
    stock_fund_items = [
        item.model_dump()
        for item in portfolio.items
        if item.type in ("STOCK", "FUND", "ETF")
    ]
    gold_fx = get_gold_fx()
    return MarketInsightService().generate(watchlist, stock_fund_items, gold_fx.model_dump())


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
    return data


@router.get("/benchmark-raw/{symbol}", response_model=List[BenchmarkPricePoint])
def get_benchmark_raw(
    symbol: str,
    start: datetime.date,
    end: datetime.date,
    session: Session = Depends(get_session),
):
    service = MarketDataService(session)
    history = service.fetch_benchmark_history(symbol, start, end)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch benchmark data")
    return [{"date": d, "price": p} for d, p in sorted(history.items())]


@router.get("/{asset_id}", response_model=List[PriceSnapshotRead])
def get_prices(asset_id: int, session: Session = Depends(get_session)):
    return session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.asset_id == asset_id)
        .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
    ).all()
