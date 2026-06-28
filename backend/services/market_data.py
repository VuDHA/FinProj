import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests

from models import Asset

KBS_HEADERS = {
    "Content-Type": "application/json",
    "x-lang": "vi",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://kbsec.com.vn/",
    "Origin": "https://kbsec.com.vn",
}


class MarketDataService:
    """Lấy dữ liệu thị trường từ các public API (KBS, VNDirect, CoinGecko)."""

    def _today(self) -> datetime.date:
        return datetime.datetime.now().date()

    def _parse_float(self, value) -> float:
        if value is None:
            return 0.0
        try:
            return float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return 0.0

    def _parse_date(self, value) -> datetime.date:
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, datetime.datetime):
            return value.date()
        try:
            return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            return self._today()

    def _parse_timestamp_date(self, ms: int) -> datetime.date:
        try:
            return datetime.datetime.fromtimestamp(ms / 1000).date()
        except Exception:
            return self._today()

    def _fetch_cafef_history(
        self,
        symbol: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Scrape lịch sử giá từ CafeF (fallback khi KBS/VNDirect lỗi)."""
        for exchange in ["HOSE", "HNX", "UPCOM"]:
            try:
                url = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"
                params = {
                    "ExchangeType": exchange,
                    "Symbol": symbol.upper(),
                    "StartDate": start.strftime("%m/%d/%Y"),
                    "EndDate": end.strftime("%m/%d/%Y"),
                    "PageIndex": 1,
                    "PageSize": 1000,
                }
                r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                if r.status_code == 200:
                    data = r.json().get("Data", {}).get("Data", [])
                    if data:
                        result = {}
                        for row in data:
                            d = datetime.datetime.strptime(row["Ngay"], "%d/%m/%Y").date()
                            # CafeF trả giá theo đơn vị nghìn đồng
                            result[d] = self._parse_float(row["GiaDongCua"]) * 1000
                        return result
            except Exception as e:
                print(f"[market_data] cafef {exchange} {symbol} error: {e}")
        return {}

    # ------------------------------------------------------------------
    # Cổ phiếu
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Fmarket - NAV quỹ mở (direct API, không cần vnstock)
    # ------------------------------------------------------------------

    _FMARKET_LISTING_CACHE: Optional[List[dict]] = None
    _FMARKET_LISTING_CACHE_TIME: Optional[datetime.datetime] = None

    def _fmarket_headers(self) -> dict:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "DNT": "1",
            "Pragma": "no-cache",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://fmarket.vn/",
            "Origin": "https://fmarket.vn/",
        }

    def _fetch_fmarket_listing(self, force: bool = False) -> List[dict]:
        if (
            not force
            and self._FMARKET_LISTING_CACHE is not None
            and self._FMARKET_LISTING_CACHE_TIME is not None
            and (datetime.datetime.now() - self._FMARKET_LISTING_CACHE_TIME).total_seconds() < 3600
        ):
            return self._FMARKET_LISTING_CACHE
        try:
            url = "https://api.fmarket.vn/res/products/filter"
            payload = {
                "types": ["NEW_FUND", "TRADING_FUND"],
                "issuerIds": [],
                "sortOrder": "DESC",
                "sortField": "navTo6Months",
                "page": 1,
                "pageSize": 100,
                "isIpo": False,
                "fundAssetTypes": [],
                "bondRemainPeriods": [],
                "searchField": "",
                "isBuyByReward": False,
                "thirdAppIds": [],
            }
            r = requests.post(url, json=payload, headers=self._fmarket_headers(), timeout=15)
            if r.status_code == 200:
                rows = r.json().get("data", {}).get("rows", [])
                MarketDataService._FMARKET_LISTING_CACHE = rows
                MarketDataService._FMARKET_LISTING_CACHE_TIME = datetime.datetime.now()
                return rows
        except Exception as e:
            print(f"[market_data] fmarket listing error: {e}")
        return self._FMARKET_LISTING_CACHE or []

    def _fetch_fmarket_nav_history(
        self, fund_id: int, start: datetime.date, end: datetime.date
    ) -> List[dict]:
        try:
            url = "https://api.fmarket.vn/res/product/get-nav-history"
            payload = {
                "isAllData": 0,
                "productId": fund_id,
                "fromDate": start.strftime("%Y%m%d"),
                "toDate": end.strftime("%Y%m%d"),
            }
            r = requests.post(url, json=payload, headers=self._fmarket_headers(), timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if isinstance(data, list):
                    return sorted(data, key=lambda x: x["navDate"])
        except Exception as e:
            print(f"[market_data] fmarket nav history {fund_id} error: {e}")
        return []

    def _fetch_fmarket_fund_direct(self, symbol: str) -> Optional[dict]:
        """Scrape NAV quỹ mở từ Fmarket API (public, không cần auth)."""
        try:
            listing = self._fetch_fmarket_listing()
            symbol_upper = symbol.upper()
            row = next(
                (
                    r
                    for r in listing
                    if r.get("shortName", "").upper() == symbol_upper
                    or r.get("code", "").upper() == symbol_upper
                ),
                None,
            )
            if not row:
                return None
            fund_id = row["id"]
            try:
                end = self._today()
                start = end - datetime.timedelta(days=14)
                nav_history = self._fetch_fmarket_nav_history(fund_id, start, end)
                if nav_history:
                    latest = nav_history[-1]
                    prev = nav_history[-2] if len(nav_history) > 1 else latest
                    price = float(latest["nav"])
                    prev_price = float(prev["nav"])
                    change = price - prev_price
                    change_percent = (change / prev_price * 100) if prev_price else 0.0
                    date = datetime.datetime.strptime(latest["navDate"], "%Y-%m-%d").date()
                    return {
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "date": date,
                    }
            except Exception as e:
                print(f"[market_data] fmarket nav {symbol} error: {e}")
            # Fallback dùng nav từ listing
            nav = float(row["nav"])
            update_at = row.get("productNavChange", {}).get("updateAt")
            date = self._parse_timestamp_date(update_at) if update_at else self._today()
            return {
                "price": nav,
                "change": 0.0,
                "change_percent": 0.0,
                "date": date,
            }
        except Exception as e:
            print(f"[market_data] fmarket direct {symbol} error: {e}")
            return None

    def fetch_fund_detail(self, symbol: str) -> Optional[dict]:
        """Trả về thông tin cơ bản của quỹ mở từ Fmarket."""
        try:
            listing = self._fetch_fmarket_listing()
            symbol_upper = symbol.upper()
            row = next(
                (
                    r
                    for r in listing
                    if r.get("shortName", "").upper() == symbol_upper
                    or r.get("code", "").upper() == symbol_upper
                ),
                None,
            )
            if not row:
                return None
            return {
                "symbol": row.get("shortName") or row.get("code"),
                "name": row.get("name"),
                "fund_type": row.get("dataFundAssetType", {}).get("name"),
                "owner": row.get("owner", {}).get("name"),
                "management_fee": row.get("managementFee"),
                "inception_date": self._parse_timestamp_date(row.get("firstIssueAt")) if row.get("firstIssueAt") else None,
                "nav": float(row.get("nav", 0)),
                "nav_update_at": self._parse_timestamp_date(row.get("productNavChange", {}).get("updateAt")) if row.get("productNavChange", {}).get("updateAt") else None,
                "vsd_fee_id": row.get("vsdFeeId"),
            }
        except Exception as e:
            print(f"[market_data] fund detail {symbol} error: {e}")
            return None

    def _fetch_fmarket_market_history(
        self, symbol: str, start: datetime.date, end: datetime.date
    ) -> Dict[datetime.date, float]:
        try:
            listing = self._fetch_fmarket_listing()
            symbol_upper = symbol.upper()
            row = next(
                (
                    r
                    for r in listing
                    if r.get("shortName", "").upper() == symbol_upper
                    or r.get("code", "").upper() == symbol_upper
                ),
                None,
            )
            if not row:
                return {}
            history = self._fetch_fmarket_nav_history(row["id"], start, end)
            return {
                datetime.datetime.strptime(h["navDate"], "%Y-%m-%d").date(): float(h["nav"])
                for h in history
            }
        except Exception as e:
            print(f"[market_data] fmarket market history {symbol} error: {e}")
            return {}

    def fetch_market_history(
        self,
        symbol: str,
        type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Trả về lịch sử giá/NAV cho mã thị trường."""
        if type == "FUND":
            history = self._fetch_fmarket_market_history(symbol, start, end)
            if history:
                return history
            return {}
        return self.fetch_history(symbol, start, end)

    def _fetch_cafef_current_stock(self, symbol: str) -> Optional[dict]:
        """Scrape giá đóng cửa gần nhất từ CafeF (nghìn đồng)."""
        try:
            end = self._today()
            start = end - datetime.timedelta(days=14)
            history = self._fetch_cafef_history(symbol, start, end)
            if not history:
                return None
            dates = sorted(history.keys())
            latest_date = dates[-1]
            latest = history[latest_date]
            prev = history[dates[-2]] if len(dates) > 1 else latest
            change = latest - prev
            change_percent = (change / prev * 100) if prev else 0.0
            return {
                "price": latest,
                "change": change,
                "change_percent": change_percent,
                "date": latest_date,
            }
        except Exception as e:
            print(f"[market_data] cafef current {symbol} error: {e}")
            return None

    def fetch_stock_price(self, symbol: str) -> Optional[dict]:
        # Thử KBS price board trước (real-time)
        try:
            url = "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stock/iss"
            r = requests.post(
                url,
                json={"code": symbol.upper()},
                headers=KBS_HEADERS,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    price = self._parse_float(item.get("CP"))
                    if price <= 0:
                        price = self._parse_float(item.get("RE"))
                    change = self._parse_float(item.get("CH"))
                    change_percent = self._parse_float(item.get("CHP"))
                    return {
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "date": self._today(),
                    }
        except Exception as e:
            print(f"[market_data] kbs price board {symbol} error: {e}")

        # Fallback 2: CafeF scraping (lấy lịch sử 14 ngày gần nhất)
        try:
            end = self._today()
            start = end - datetime.timedelta(days=14)
            history = self._fetch_cafef_history(symbol, start, end)
            if history:
                latest_date = max(history.keys())
                latest = history[latest_date]
                prev_date = sorted(history.keys())[-2] if len(history) > 1 else latest_date
                prev = history[prev_date]
                change = latest - prev
                change_percent = (change / prev * 100) if prev else 0.0
                return {
                    "price": latest,
                    "change": change,
                    "change_percent": change_percent,
                    "date": self._today(),
                }
        except Exception as e:
            print(f"[market_data] cafef current {symbol} error: {e}")

        # Fallback 3: VNDirect finfo historical (lấy ngày gần nhất)
        try:
            url = "https://finfo-api.vndirect.com.vn/v4/stock_prices/"
            end = self._today()
            start = end - datetime.timedelta(days=14)
            params = {
                "q": f"code:{symbol.upper()}~date:gte:{start.strftime('%Y-%m-%d')}~date:lte:{end.strftime('%Y-%m-%d')}",
                "sort": "date",
                "size": 30,
                "page": 1,
            }
            r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                if items:
                    latest = items[-1]
                    prev = items[-2] if len(items) > 1 else latest
                    price = self._parse_float(latest.get("close"))
                    prev_price = self._parse_float(prev.get("close")) or price
                    change = price - prev_price
                    change_percent = (change / prev_price * 100) if prev_price else 0.0
                    return {
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "date": self._today(),
                    }
        except Exception as e:
            print(f"[market_data] vndirect fallback {symbol} error: {e}")

        return None

    def fetch_quote(self, symbol: str) -> dict:
        # Ưu tiên Fmarket cho quỹ mở, KBS cho cổ phiếu/ETF
        price = self._fetch_fmarket_fund_direct(symbol) or self.fetch_stock_price(symbol)
        if price:
            return {
                "symbol": symbol.upper(),
                "price": price["price"],
                "change": price["change"],
                "change_percent": price["change_percent"],
                "date": price["date"],
            }
        return {
            "symbol": symbol.upper(),
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "date": self._today(),
        }

    def fetch_quotes(self, symbols: List[str]) -> List[dict]:
        """Fetch giá nhiều mã cùng lúc bằng đa luồng."""
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_symbol = {executor.submit(self.fetch_quote, s): s for s in symbols}
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
                            "date": self._today(),
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
                    "date": self._today(),
                },
            )
            for s in symbols
        ]

    def fetch_history(
        self,
        symbol: str,
        start: datetime.date,
        end: datetime.date,
        interval: str = "day",
    ) -> Dict[datetime.date, float]:
        """Trả về dict {date: close_price} cho một mã."""
        # Thử KBS trước
        try:
            url = f"https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{symbol.upper()}/data_{interval}"
            params = {
                "sdate": start.strftime("%d-%m-%Y"),
                "edate": end.strftime("%d-%m-%Y"),
            }
            r = requests.get(url, params=params, headers=KBS_HEADERS, timeout=15)
            if r.status_code == 200:
                payload = r.json()
                rows = payload.get("data_day", payload.get(f"data_{interval}", []))
                result = {}
                for row in rows:
                    t = row.get("t", "")
                    if len(t) >= 10:
                        d = datetime.datetime.strptime(t[:10], "%Y-%m-%d").date()
                        result[d] = self._parse_float(row.get("c"))
                if result:
                    return result
        except Exception as e:
            print(f"[market_data] kbs history {symbol} error: {e}")

        # Fallback 2: CafeF scraping
        try:
            history = self._fetch_cafef_history(symbol, start, end)
            if history:
                return history
        except Exception as e:
            print(f"[market_data] cafef history {symbol} error: {e}")

        # Fallback 3: VNDirect finfo
        try:
            url = "https://finfo-api.vndirect.com.vn/v4/stock_prices/"
            params = {
                "q": f"code:{symbol.upper()}~date:gte:{start.strftime('%Y-%m-%d')}~date:lte:{end.strftime('%Y-%m-%d')}",
                "sort": "date",
                "size": 1000,
                "page": 1,
            }
            r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", [])
                result = {}
                for item in items:
                    d = datetime.datetime.strptime(item["date"], "%Y-%m-%d").date()
                    result[d] = self._parse_float(item.get("close"))
                if result:
                    return result
        except Exception as e:
            print(f"[market_data] vndirect history {symbol} error: {e}")

        return {}

    # ------------------------------------------------------------------
    # Benchmark indexes (VN-Index, etc.)
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
                        result[d] = self._parse_float(close)
                    if result:
                        self._BENCHMARK_CACHE[cache_key] = result
                        self._BENCHMARK_CACHE_TIME = datetime.datetime.now()
                        return result
        except Exception as e:
            print(f"[market_data] dchart benchmark {symbol} error: {e}")

        return {}

    # ------------------------------------------------------------------
    # Vàng
    # ------------------------------------------------------------------

    def fetch_gold_price(self) -> Optional[dict]:
        try:
            from services.gold_fx import get_gold_fx
            data = get_gold_fx()
            if data.gold:
                first = data.gold[0]
                return {
                    "price": first.buy,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "date": self._today(),
                }
        except Exception as e:
            print(f"[market_data] gold error: {e}")
        return None

    # ------------------------------------------------------------------
    # Danh sách mã niêm yết
    # ------------------------------------------------------------------

    def fetch_all_stocks(self) -> List[dict]:
        """Lấy danh sách cổ phiếu/ETF niêm yết trên sàn từ CafeF."""
        results = []
        try:
            url = "https://cafefnew.mediacdn.vn/Search/company.json"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                items = r.json()
                for item in items:
                    redirect = item.get("RedirectUrl", "")
                    exchange = None
                    if "/hose/" in redirect:
                        exchange = "HOSE"
                    elif "/hastc/" in redirect or "/hnx/" in redirect:
                        exchange = "HNX"
                    elif "/upcom/" in redirect:
                        exchange = "UPCOM"
                    if not exchange:
                        continue
                    symbol = item.get("Symbol", "")
                    title = item.get("Title", "")
                    if not symbol:
                        continue
                    # Bỏ qua các mã được phân loại là quỹ/ETF (sẽ lấy từ Fmarket endpoint)
                    title_lower = title.lower()
                    is_fund = any(
                        kw in title_lower for kw in ["etf", "quỹ", "fund", "ccq", "chứng chỉ quỹ"]
                    )
                    if is_fund:
                        continue
                    results.append(
                        {
                            "symbol": symbol,
                            "name": title,
                            "exchange": exchange,
                            "type": "STOCK",
                        }
                    )
        except Exception as e:
            print(f"[market_data] fetch_all_stocks error: {e}")
        return results

    def fetch_all_funds(self) -> List[dict]:
        """Lấy danh sách quỹ mở từ Fmarket."""
        results = []
        try:
            fmarket_listing = self._fetch_fmarket_listing()
            for row in fmarket_listing:
                symbol = row.get("shortName") or row.get("code")
                name = row.get("name")
                if not symbol or not name:
                    continue
                results.append(
                    {
                        "symbol": symbol,
                        "name": name,
                        "exchange": "FMARKET",
                        "type": "FUND",
                    }
                )
        except Exception as e:
            print(f"[market_data] fetch_all_funds error: {e}")
        return results

    def fetch_all_symbols(self) -> List[dict]:
        """Lấy danh sách tất cả mã cổ phiếu và quỹ mở."""
        return self.fetch_all_stocks() + self.fetch_all_funds()

    # ------------------------------------------------------------------
    # Crypto
    # ------------------------------------------------------------------

    def fetch_crypto_price(self, symbol: str) -> Optional[dict]:
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
        }
        coin_id = mapping.get(symbol.upper(), symbol.lower())
        try:
            url = (
                "https://api.coingecko.com/api/v3/simple/price"
                f"?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            )
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get(coin_id, {})
                price = float(data.get("usd", 0))
                change_percent = float(data.get("usd_24h_change") or 0)
                return {
                    "price": price,
                    "change": 0.0,
                    "change_percent": change_percent,
                    "date": self._today(),
                }
        except Exception as e:
            print(f"[market_data] crypto {symbol} error: {e}")
        return None

    # ------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        if asset.type == "CRYPTO":
            return self.fetch_crypto_price(asset.symbol)
        if asset.type == "GOLD":
            return self.fetch_gold_price()
        if asset.type == "FUND":
            return self._fetch_fmarket_fund_direct(asset.symbol) or self.fetch_stock_price(asset.symbol) or self._fetch_cafef_current_stock(asset.symbol)
        return self.fetch_stock_price(asset.symbol) or self._fetch_cafef_current_stock(asset.symbol)
