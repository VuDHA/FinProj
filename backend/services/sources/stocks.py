import datetime
from typing import Dict, Optional

import requests

from models import Asset
from services.sources.base import Source
from services.sources.utils import KBS_HEADERS, cafef_headers, parse_float, today


class KbsStockSource(Source):
    code = "kbs"
    name = "KBS Securities"
    description = "Bảng giá real-time từ KBS Securities (KB Việt Nam)."
    supported_types = ["STOCK", "ETF"]
    supports_history = True

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            url = "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stock/iss"
            r = requests.post(
                url,
                json={"code": asset.symbol.upper()},
                headers=KBS_HEADERS,
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    price = parse_float(item.get("CP"))
                    if price <= 0:
                        price = parse_float(item.get("RE"))
                    change = parse_float(item.get("CH"))
                    change_percent = parse_float(item.get("CHP"))
                    return {
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "date": today(),
                    }
        except Exception as e:
            print(f"[source kbs] price {asset.symbol} error: {e}")
        return None

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        try:
            url = f"https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{symbol.upper()}/data_day"
            params = {
                "sdate": start.strftime("%d-%m-%Y"),
                "edate": end.strftime("%d-%m-%Y"),
            }
            r = requests.get(url, params=params, headers=KBS_HEADERS, timeout=15)
            if r.status_code == 200:
                payload = r.json()
                rows = payload.get("data_day", [])
                result = {}
                for row in rows:
                    t = row.get("t", "")
                    if len(t) >= 10:
                        d = datetime.datetime.strptime(t[:10], "%Y-%m-%d").date()
                        result[d] = parse_float(row.get("c"))
                if result:
                    return result
        except Exception as e:
            print(f"[source kbs] history {symbol} error: {e}")
        return {}


class CafefStockSource(Source):
    code = "cafef"
    name = "CafeF"
    description = "Lịch sử giá đóng cửa từ CafeF (phù hợp cho lịch sử dài hạn)."
    supported_types = ["STOCK", "ETF"]
    supports_history = True
    supports_listing = True

    def _fetch_cafef_history(
        self,
        symbol: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
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
                r = requests.get(url, params=params, headers=cafef_headers(), timeout=15)
                if r.status_code == 200:
                    data = r.json().get("Data", {}).get("Data", [])
                    if data:
                        result = {}
                        for row in data:
                            d = datetime.datetime.strptime(row["Ngay"], "%d/%m/%Y").date()
                            # CafeF trả giá theo đơn vị nghìn đồng
                            result[d] = parse_float(row["GiaDongCua"]) * 1000
                        return result
            except Exception as e:
                print(f"[source cafef] {exchange} {symbol} error: {e}")
        return {}

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            end = today()
            start = end - datetime.timedelta(days=14)
            history = self._fetch_cafef_history(asset.symbol, start, end)
            if not history:
                return None
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
                "date": today(),
            }
        except Exception as e:
            print(f"[source cafef] current {asset.symbol} error: {e}")
            return None

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        return self._fetch_cafef_history(symbol, start, end)

    def fetch_listing(self) -> list:
        results = []
        try:
            url = "https://cafefnew.mediacdn.vn/Search/company.json"
            r = requests.get(url, timeout=10, headers=cafef_headers())
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
            print(f"[source cafef] listing error: {e}")
        return results

