import datetime
from typing import Dict, List, Optional

import requests

from common.models import Asset
from services.market.sources.base import Source
from services.market.sources.utils import parse_float, today


TCBS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


class TcbsSource(Source):
    """Dữ liệu cổ phiếu/quỹ/ETF từ TCBS (Techcom Securities).

    TCBS từng công khai các endpoint tại apipubaws.tcbs.com.vn. Một số endpoint
    có thể không khả dụng ở thời điểm hiện tại; nguồn này sẽ tự động fall back
    về các nguồn khác trong registry khi gặp lỗi.
    """

    code = "tcbs"
    name = "TCBS"
    description = "Dữ liệu cổ phiếu/quỹ/ETF từ TCBS (Techcom Securities)."
    supported_types = ["STOCK", "FUND", "ETF"]
    supports_history = True
    supports_listing = True

    def _fetch_bars(
        self, symbol: str, start: datetime.date, end: datetime.date
    ) -> Dict[datetime.date, float]:
        try:
            end_dt = datetime.datetime.combine(end, datetime.time.max)
            to_ts = int(end_dt.timestamp())
            days = (end - start).days + 1
            url = (
                "https://apipubaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term"
                f"?ticker={symbol.upper()}&type=stock&resolution=D"
                f"&to={to_ts}&countBack={days}"
            )
            r = requests.get(url, headers=TCBS_HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                result = {}
                for row in data:
                    trading_date = row.get("tradingDate")
                    close = row.get("close")
                    if not trading_date or close is None:
                        continue
                    d = _parse_trading_date(trading_date)
                    if d and start <= d <= end:
                        result[d] = parse_float(close)
                if result:
                    return result
        except Exception as e:
            print(f"[source tcbs] bars {symbol} error: {e}")
        return {}

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            end = today()
            start = end - datetime.timedelta(days=14)
            history = self._fetch_bars(asset.symbol, start, end)
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
                "date": latest_date,
                "metadata": {"source": "tcbs"},
            }
        except Exception as e:
            print(f"[source tcbs] price {asset.symbol} error: {e}")
        return None

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        return self._fetch_bars(symbol, start, end)

    def fetch_listing(self) -> List[dict]:
        results = []
        offset = 0
        limit = 1000
        try:
            while True:
                url = (
                    "https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/all"
                    f"?offset={offset}&limit={limit}"
                )
                r = requests.get(url, headers=TCBS_HEADERS, timeout=15)
                if r.status_code != 200:
                    break
                items = r.json().get("data", [])
                if not items:
                    break
                for item in items:
                    symbol = item.get("ticker")
                    name = item.get("org_name") or item.get("short_name") or symbol
                    exchange = item.get("exchange") or ""
                    if not symbol:
                        continue
                    results.append(
                        {
                            "symbol": symbol,
                            "name": name,
                            "exchange": exchange,
                            "type": "STOCK",
                            "metadata": item,
                        }
                    )
                if len(items) < limit:
                    break
                offset += limit
        except Exception as e:
            print(f"[source tcbs] listing error: {e}")
        return results


def _parse_trading_date(value) -> Optional[datetime.date]:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value / 1000).date()
        except Exception:
            pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(str(value), fmt).date()
        except Exception:
            continue
    return None
