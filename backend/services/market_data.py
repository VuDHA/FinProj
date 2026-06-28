import contextlib
import datetime
import io
import sys
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

    @contextlib.contextmanager
    def _suppress_output(self):
        import os

        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
        try:
            yield
        finally:
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)

    def _parse_date(self, value) -> datetime.date:
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, datetime.datetime):
            return value.date()
        try:
            return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
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

    def _fetch_vnstock_stock(self, symbol: str) -> Optional[dict]:
        """Scrape giá cổ phiếu từ vnstock (VCI/TCBS). Giá trả về theo nghìn đồng."""
        try:
            with self._suppress_output():
                from vnstock.api.quote import Quote
                import pandas as pd

            q = Quote(symbol=symbol.upper(), source="VCI", show_log=False)
            end = self._today()
            start = end - datetime.timedelta(days=30)
            df = q.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
            if df is None or df.empty:
                return None
            df = df.sort_values("time").reset_index(drop=True)
            latest = df.iloc[-1]
            price = float(latest["close"]) * 1000
            ts = latest["time"]
            date = ts.date() if hasattr(ts, "date") else pd.to_datetime(ts).date()
            if len(df) >= 2:
                prev = df.iloc[-2]
                prev_price = float(prev["close"]) * 1000
                change = price - prev_price
                change_percent = (change / prev_price * 100) if prev_price else 0.0
            else:
                change = 0.0
                change_percent = 0.0
            return {
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "date": date,
            }
        except Exception as e:
            print(f"[market_data] vnstock stock {symbol} error: {e}")
            return None

    def _fetch_fmarket_fund(self, symbol: str) -> Optional[dict]:
        """Scrape NAV quỹ mở từ Fmarket qua vnstock."""
        try:
            with self._suppress_output():
                from vnstock import Fund
                import pandas as pd

            fund = Fund()
            listing = fund.listing()
            symbol_upper = symbol.upper()
            mask = (listing["short_name"].str.upper() == symbol_upper) | (
                listing["fund_code"].str.upper() == symbol_upper
            )
            match = listing[mask]
            if match.empty:
                return None
            row = match.iloc[0]
            fund_id = row["fund_id_fmarket"]
            try:
                nav_history = fund.nav_report(str(fund_id)).sort_values("date")
                if not nav_history.empty and len(nav_history) >= 1:
                    latest = nav_history.iloc[-1]
                    price = float(latest["nav_per_unit"])
                    date = latest["date"]
                    if len(nav_history) >= 2:
                        prev = nav_history.iloc[-2]
                        prev_price = float(prev["nav_per_unit"])
                        change = price - prev_price
                        change_percent = (change / prev_price * 100) if prev_price else 0.0
                    else:
                        change = 0.0
                        change_percent = 0.0
                    return {
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "date": self._parse_date(date),
                    }
            except Exception as e:
                print(f"[market_data] fmarket nav_report {symbol} error: {e}")
            # fallback dùng nav từ listing
            nav = float(row["nav"])
            date = row["nav_update_at"]
            return {
                "price": nav,
                "change": 0.0,
                "change_percent": 0.0,
                "date": self._parse_date(date),
            }
        except Exception as e:
            print(f"[market_data] fmarket {symbol} error: {e}")
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
        price = self._fetch_fmarket_fund(symbol) or self.fetch_stock_price(symbol)
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

    def fetch_all_symbols(self) -> List[dict]:
        """Lấy danh sách tất cả mã cổ phiếu và chứng chỉ quỹ đang niêm yết từ CafeF."""
        try:
            url = "https://cafefnew.mediacdn.vn/Search/company.json"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return []
            items = r.json()
            results = []
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
                # Phân loại chứng chỉ quỹ / ETF qua tên
                title_lower = title.lower()
                is_fund = any(
                    kw in title_lower for kw in ["etf", "quỹ", "fund", "ccq", "chứng chỉ quỹ"]
                )
                results.append(
                    {
                        "symbol": symbol,
                        "name": title,
                        "exchange": exchange,
                        "type": "FUND" if is_fund else "STOCK",
                    }
                )
            return results
        except Exception as e:
            print(f"[market_data] fetch_all_symbols error: {e}")
            return []

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
            return self._fetch_fmarket_fund(asset.symbol) or self._fetch_vnstock_stock(asset.symbol) or self.fetch_stock_price(asset.symbol)
        return self._fetch_vnstock_stock(asset.symbol) or self.fetch_stock_price(asset.symbol)
