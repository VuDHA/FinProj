import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests

from common.date_utils import parse_float, today
from common.models import Asset, PriceSnapshot
from common.asset_type_config import is_market_price_type
from services.market.source_selector import SourceSelector
from services.market.sources import registry
from sqlmodel import Session, select


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

    def resolve_historical_price(
        self, asset: Asset, date: datetime.date
    ) -> Optional[float]:
        """Return the best market price for `asset` on `date`.

        For historical dates the current live price is intentionally avoided,
        because using today's price as a past cost basis makes PnL look like 0%.
        """
        # Latest stored snapshot on or before the date.
        snapshot = self.session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == asset.id, PriceSnapshot.date <= date)
            .order_by(PriceSnapshot.date.desc())
        ).first()
        if snapshot and snapshot.price > 0:
            return snapshot.price

        # Historical price for the exact date from a market source.
        if is_market_price_type(self.session, asset.type):
            history = self.selector.fetch_history(asset, date, date)
            price = history.get(date)
            if price and price > 0:
                return price

        # Earliest stored snapshot on or after the date (closest available).
        snapshot = self.session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == asset.id, PriceSnapshot.date >= date)
            .order_by(PriceSnapshot.date.asc())
        ).first()
        if snapshot and snapshot.price > 0:
            return snapshot.price

        # Current live price is only acceptable as a fallback for today.
        if date >= today():
            data = self.fetch_price(asset)
            if data and data.get("price", 0) > 0:
                return data["price"]

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
                "date": data.get("date", today()),
            }
        return {
            "symbol": symbol.upper(),
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "date": today(),
            "error": warnings[-1] if warnings else "Failed to fetch market data",
        }

    def fetch_quotes(self, symbols: List[str], asset_type: str = "STOCK") -> List[dict]:
        """Fetch giá nhiều mã cùng lúc bằng đa luồng."""
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_symbol = {
                executor.submit(self.fetch_quote, s, asset_type): s for s in symbols
            }
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    print(f"[market_data] quote thread {symbol} error: {e}")
                    results.append(
                        {
                            "symbol": symbol.upper(),
                            "price": 0.0,
                            "change": 0.0,
                            "change_percent": 0.0,
                            "date": today(),
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
                    "date": today(),
                    "error": "Failed to fetch market data",
                },
            )
            for s in symbols
        ]

    def fetch_quotes_for_assets(self, assets: List[Asset]) -> List[dict]:
        """Fetch prices for concrete Asset objects, respecting asset.source."""
        # Pre-fetch defaults so worker threads do not race on the shared session.
        self.selector._get_defaults()

        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_asset = {
                executor.submit(self.fetch_price_with_warnings, asset): asset
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
                                "date": data.get("date", today()),
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
                                "date": today(),
                                "warnings": warnings,
                            }
                        )
                except Exception as e:
                    print(f"[market_data] quote_for_asset thread {asset.symbol} error: {e}")
                    results.append(
                        {
                            "symbol": asset.symbol.upper(),
                            "price": None,
                            "change": None,
                            "change_percent": None,
                            "date": today(),
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
                    "date": today(),
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
            ).order_by(PriceSnapshot.date.asc())
        ).all()
        existing_map = {s.date: s for s in snapshots}

        # If we already have enough data for the requested range, return it.
        if snapshots:
            span = (end - start).days + 1
            if len(snapshots) >= span * 0.5:
                return {s.date: s.price for s in snapshots}

        # Otherwise fetch live data and backfill into the database.
        live = self.fetch_market_history(symbol, asset_type, start, end)
        if live:
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
                print(f"[market_data] fund_detail {symbol} via {source.code} error: {e}")
        return None

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
                        result[d] = parse_float(close)
                    if result:
                        self._BENCHMARK_CACHE[cache_key] = result
                        self._BENCHMARK_CACHE_TIME = datetime.datetime.now()
                        return result
        except Exception as e:
            print(f"[market_data] dchart benchmark {symbol} error: {e}")

        return {}

