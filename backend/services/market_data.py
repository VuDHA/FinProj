import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import requests

from models import Asset, PriceSnapshot
from services.asset_type_config import is_market_price_type
from services.source_selector import SourceSelector
from services.sources import registry
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


def _today() -> datetime.date:
    return datetime.datetime.now().date()


def _parse_price_value(raw: str) -> float:
    """Parse a price string that may use comma as decimal or thousands separator."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(" ", "")
    if not s:
        return 0.0
    for sym in ("₫", "$", "€", "£", "¥", "VND", "USD", "EUR"):
        s = s.replace(sym, "")
    s = s.strip()
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        s = s.replace(",", "")
    elif has_comma:
        parts = s.rsplit(",", 1)
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0].replace(",", "") + "." + parts[1]
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_float(value) -> float:
    return _parse_price_value(value)


class MarketDataService:
    """Facade lấy dữ liệu thị trường qua registry các nguồn dữ liệu có thể cấu hình."""

    def __init__(self, session: Session):
        self.session = session
        self.selector = SourceSelector(session)

    def _ensure_asset(self, symbol: str, asset_type: str) -> Asset:
        symbol = symbol.upper()
        asset = self.session.exec(
            select(Asset).where(Asset.symbol == symbol, Asset.type == asset_type)
        ).first()
        if asset:
            return asset
        asset = Asset(symbol=symbol, type=asset_type, name=symbol, is_active=True)
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def _save_history(
        self,
        asset_id: int,
        history: Dict[datetime.date, float],
        existing: Optional[Dict[datetime.date, "PriceSnapshot"]] = None,
    ) -> None:
        if not history:
            return
        existing = existing or {}
        for d, price in sorted(history.items()):
            if price <= 0:
                continue
            snapshot = existing.get(d)
            if snapshot:
                snapshot.price = price
            else:
                self.session.add(
                    PriceSnapshot(asset_id=asset_id, date=d, price=price)
                )
        self.session.commit()

    # ------------------------------------------------------------------
    # Price API
    # ------------------------------------------------------------------

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        if not is_market_price_type(self.session, asset.type):
            return None
        data, _ = self.selector.fetch_price(asset)
        return data

    def fetch_price_with_warnings(self, asset: Asset) -> Tuple[Optional[dict], List[str]]:
        if not is_market_price_type(self.session, asset.type):
            return None, [f"Asset type {asset.type} does not support automatic price fetch"]
        return self.selector.fetch_price(asset)

    def resolve_effective_price(
        self, asset: Asset, date: datetime.date, input_price: Optional[float]
    ) -> Optional[Decimal]:
        """Return the price to use for calculations and storage.

        Priority:
        1. The user-provided input price if it is positive.
        2. A resolved market price for market-priced assets.
        3. None if no price can be determined.
        """
        if input_price and input_price > 0:
            return Decimal(str(input_price)) if not isinstance(input_price, Decimal) else input_price
        if not is_market_price_type(self.session, asset.type):
            return None
        return self.resolve_historical_price(asset, date)

    def resolve_historical_price(
        self, asset: Asset, date: datetime.date
    ) -> Optional[Decimal]:
        """Return the best market price for `asset` on `date`.

        For historical dates the current live price is intentionally avoided,
        because using today's price as a past cost basis makes PnL look like 0%.
        """
        # Latest stored snapshot on or before the date.
        snapshot = self.session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == asset.id, PriceSnapshot.date <= date)
            .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
        ).first()
        if snapshot and snapshot.price > 0:
            return snapshot.price

        # Historical price for the exact date from a market source.
        if is_market_price_type(self.session, asset.type):
            history = self.selector.fetch_history(asset, date, date)
            price = history.get(date)
            if price and price > 0:
                return Decimal(str(price)) if not isinstance(price, Decimal) else price

        # Earliest stored snapshot on or after the date (closest available).
        snapshot = self.session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == asset.id, PriceSnapshot.date >= date)
            .order_by(PriceSnapshot.date.asc(), PriceSnapshot.id.asc())
        ).first()
        if snapshot and snapshot.price > 0:
            return snapshot.price

        # Current live price is only acceptable as a fallback for today.
        if date >= _today():
            data = self.fetch_price(asset)
            if data and data.get("price", 0) > 0:
                price = data["price"]
                return Decimal(str(price)) if not isinstance(price, Decimal) else price

        return None

    def fetch_quote(self, symbol: str, asset_type: str = "STOCK") -> dict:
        asset = Asset(symbol=symbol, type=asset_type, name=symbol, is_active=True)
        data, warnings = self.selector.fetch_price(asset)
        if data:
            return {
                "symbol": symbol.upper(),
                "price": data["price"],
                "change": data.get("change"),
                "change_percent": data.get("change_percent"),
                "date": data.get("date", _today()),
            }
        return {
            "symbol": symbol.upper(),
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "date": _today(),
            "error": warnings[-1] if warnings else "Failed to fetch market data",
        }

    def _fetch_quote_threaded(self, symbol: str, asset_type: str) -> dict:
        """Run fetch_quote on a dedicated Session so worker threads never share
        self.session (SQLite sessions are not thread-safe and concurrent use
        raises sqlite3.InterfaceError: bad parameter or other API misuse)."""
        from database import engine

        with Session(engine) as session:
            return MarketDataService(session).fetch_quote(symbol, asset_type)

    def fetch_quotes(self, symbols: List[str], asset_type: str = "STOCK") -> List[dict]:
        """Fetch giá nhiều mã cùng lúc bằng đa luồng."""
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_symbol = {
                executor.submit(self._fetch_quote_threaded, s, asset_type): s
                for s in symbols
            }
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error("market_data quote thread %s error: %s", symbol, e)
                    results.append(
                        {
                            "symbol": symbol.upper(),
                            "price": 0.0,
                            "change": 0.0,
                            "change_percent": 0.0,
                            "date": _today(),
                            "error": str(e),
                        }
                    )
        # Giữ nguyên thứ tự đầu vào
        symbol_to_result = {r["symbol"]: r for r in results}
        return [
            symbol_to_result.get(
                s.upper(),
                {
                    "symbol": s.upper(),
                    "price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "date": _today(),
                    "error": "Failed to fetch market data",
                },
            )
            for s in symbols
        ]

    def _fetch_price_with_warnings_threaded(
        self, asset: Asset
    ) -> Tuple[Optional[dict], List[str]]:
        """Run fetch_price_with_warnings on a dedicated Session so worker
        threads never share self.session (SQLite sessions are not thread-safe
        and concurrent use raises sqlite3.InterfaceError)."""
        from database import engine

        with Session(engine) as session:
            return MarketDataService(session).fetch_price_with_warnings(asset)

    def fetch_quotes_for_assets(self, assets: List[Asset]) -> List[dict]:
        """Fetch prices for concrete Asset objects, respecting asset.source."""
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_asset = {
                executor.submit(self._fetch_price_with_warnings_threaded, asset): asset
                for asset in assets
            }
            for future in as_completed(future_to_asset):
                asset = future_to_asset[future]
                try:
                    data, warnings = future.result()
                    if data:
                        results.append(
                            {
                                "symbol": asset.symbol.upper(),
                                "price": data["price"],
                                "change": data.get("change"),
                                "change_percent": data.get("change_percent"),
                                "date": data.get("date", _today()),
                                "warnings": warnings,
                            }
                        )
                    else:
                        results.append(
                            {
                                "symbol": asset.symbol.upper(),
                                "price": None,
                                "change": None,
                                "change_percent": None,
                                "date": _today(),
                                "warnings": warnings,
                            }
                        )
                except Exception as e:
                    logger.error("market_data quote_for_asset thread %s error: %s", asset.symbol, e)
                    results.append(
                        {
                            "symbol": asset.symbol.upper(),
                            "price": None,
                            "change": None,
                            "change_percent": None,
                            "date": _today(),
                            "warnings": [str(e)],
                        }
                    )
        # Giữ nguyên thứ tự đầu vào
        symbol_to_result = {r["symbol"]: r for r in results}
        return [
            symbol_to_result.get(
                a.symbol.upper(),
                {
                    "symbol": a.symbol.upper(),
                    "price": None,
                    "change": None,
                    "change_percent": None,
                    "date": _today(),
                    "warnings": [],
                },
            )
            for a in assets
        ]

    # ------------------------------------------------------------------
    # History / listing
    # ------------------------------------------------------------------

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        asset = Asset(symbol=symbol, type=asset_type, name=symbol, is_active=True)
        return self.selector.fetch_history(asset, start, end)

    def fetch_market_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        asset = Asset(symbol=symbol, type=asset_type, name=symbol, is_active=True)
        return self.selector.fetch_history(asset, start, end)

    def fetch_market_history_with_backfill(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Fetch market history, backfilling into PriceSnapshot when local data is missing."""
        asset = self._ensure_asset(symbol, asset_type)
        snapshots = self.session.exec(
            select(PriceSnapshot).where(
                PriceSnapshot.asset_id == asset.id,
                PriceSnapshot.date >= start,
                PriceSnapshot.date <= end,
            ).order_by(PriceSnapshot.date.asc(), PriceSnapshot.id.asc())
        ).all()
        existing_map = {s.date: s for s in snapshots}

        # If we already have enough data for the requested range, return it.
        if snapshots:
            span = (end - start).days + 1
            if len(snapshots) >= span * 0.5:
                return {s.date: float(s.price) for s in snapshots}

        # Otherwise fetch live data and backfill into the database.
        live = self.fetch_market_history(symbol, asset_type, start, end)
        if live:
            self._save_history(asset.id, live, existing_map)
        return live

    def force_backfill_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Fetch market history and persist all missing PriceSnapshot rows for the range.

        Unlike fetch_market_history_with_backfill, this always fetches live data
        and writes any missing dates into the local snapshot table, regardless of
        how much data already exists.
        """
        asset = self._ensure_asset(symbol, asset_type)
        snapshots = self.session.exec(
            select(PriceSnapshot).where(
                PriceSnapshot.asset_id == asset.id,
                PriceSnapshot.date >= start,
                PriceSnapshot.date <= end,
            ).order_by(PriceSnapshot.date.asc(), PriceSnapshot.id.asc())
        ).all()
        existing_map = {s.date: s for s in snapshots}

        live = self.fetch_market_history(symbol, asset_type, start, end)
        if not live:
            return {}

        self._save_history(asset.id, live, existing_map)
        return live

    def fetch_all_stocks(self) -> List[dict]:
        return self.selector.fetch_listing("STOCK")

    def fetch_all_funds(self) -> List[dict]:
        return self.selector.fetch_listing("FUND")

    def fetch_all_symbols(self) -> List[dict]:
        return self.fetch_all_stocks() + self.fetch_all_funds()

    # ------------------------------------------------------------------
    # Fund detail
    # ------------------------------------------------------------------

    def fetch_fund_detail(self, symbol: str) -> Optional[dict]:
        for source in registry.for_type("FUND"):
            if not hasattr(source, "fetch_fund_detail"):
                continue
            try:
                data = source.fetch_fund_detail(symbol)
                if data:
                    return data
            except Exception as e:
                logger.error("market_data fund_detail %s via %s error: %s", symbol, source.code, e)
        return None

    def fetch_stock_detail(self, symbol: str) -> Optional[dict]:
        symbol = symbol.upper()
        listing = self.fetch_all_stocks()
        stock = next((s for s in listing if s.get("symbol", "").upper() == symbol), None)
        if not stock:
            return None

        try:
            quote = self.fetch_quotes([symbol], asset_type="STOCK")[0]
        except Exception as e:
            logger.error("market_data stock_detail quote %s error: %s", symbol, e)
            quote = None

        result = {
            "symbol": symbol,
            "name": stock.get("name", symbol),
            "exchange": stock.get("exchange", ""),
            "type": "STOCK",
            "sector": None,
            "industry": None,
            "market_cap": None,
            "price": quote.get("price", 0.0) if quote else 0.0,
            "change": quote.get("change", 0.0) if quote else 0.0,
            "change_percent": quote.get("change_percent", 0.0) if quote else 0.0,
            "date": quote.get("date") if quote else _today(),
            "pe": None,
            "pb": None,
            "dividend_yield": None,
        }

        # Try to enrich with VNDirect finfo data.
        def _to_float(v):
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        try:
            url = f"https://finfo-api.vndirect.com.vn/v4/stocks?sort=code:asc&q=code:{symbol}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    info = data[0]
                    result["sector"] = info.get("sector") or None
                    result["industry"] = info.get("industry") or None
                    result["market_cap"] = _to_float(info.get("marketCap"))
                    result["pe"] = _to_float(info.get("pe"))
                    result["pb"] = _to_float(info.get("pb"))
                    result["dividend_yield"] = _to_float(info.get("dividendYield"))
        except Exception as e:
            logger.error("market_data stock_detail vndirect %s error: %s", symbol, e)

        return result

    # ------------------------------------------------------------------
    # Benchmark indexes
    # ------------------------------------------------------------------

    _BENCHMARK_CACHE: Dict[str, Dict[datetime.date, float]] = {}
    _BENCHMARK_CACHE_TIME: Optional[datetime.datetime] = None

    def fetch_benchmark_history(
        self,
        symbol: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Trả về lịch sử chỉ số tham chiếu (VD: VNINDEX) từ VNDirect dchart API."""
        cache_key = f"{symbol.upper()}:{start}:{end}"
        if (
            cache_key in self._BENCHMARK_CACHE
            and self._BENCHMARK_CACHE_TIME
            and (datetime.datetime.now() - self._BENCHMARK_CACHE_TIME).total_seconds() < 86400
        ):
            return self._BENCHMARK_CACHE[cache_key]

        try:
            start_ts = int(datetime.datetime.combine(start, datetime.time.min).timestamp())
            end_ts = int(datetime.datetime.combine(end, datetime.time.max).timestamp())
            url = "https://dchart-api.vndirect.com.vn/dchart/history"
            params = {
                "resolution": "D",
                "symbol": symbol.upper(),
                "from": start_ts,
                "to": end_ts,
            }
            r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code == 200:
                payload = r.json()
                timestamps = payload.get("t", [])
                closes = payload.get("c", [])
                if timestamps and closes and len(timestamps) == len(closes):
                    result = {}
                    for ts, close in zip(timestamps, closes):
                        d = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).date()
                        result[d] = _parse_float(close)
                    if result:
                        self._BENCHMARK_CACHE[cache_key] = result
                        self._BENCHMARK_CACHE_TIME = datetime.datetime.now()
                        return result
        except Exception as e:
            logger.error("market_data dchart benchmark %s error: %s", symbol, e)

        return {}

