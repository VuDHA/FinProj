import datetime
import logging
from typing import Dict, List, Optional

import requests

from models import Asset
from services.sources.base import Source
from services.sources.utils import parse_float, today

logger = logging.getLogger(__name__)


DNSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


class DnseSource(Source):
    """Dữ liệu giá cổ phiếu/ETF từ DNSE (qua Entrade public chart API).

    DNSE công khai dữ liệu lịch sử OHLC qua services.entrade.com.vn. Nguồn này
    phù hợp làm nguồn phụ/backup cho giá và lịch sử STOCK/ETF; không hỗ trợ FUND.
    """

    code = "dnse"
    name = "DNSE"
    description = "Dữ liệu lịch sử và giá gần nhất từ DNSE (Entrade chart API)."
    supported_types = ["STOCK", "ETF"]
    supports_history = True
    supports_listing = False

    def _fetch_ohlcs(
        self, symbol: str, start: datetime.date, end: datetime.date
    ) -> Dict[datetime.date, float]:
        try:
            start_dt = datetime.datetime.combine(start, datetime.time.min)
            end_dt = datetime.datetime.combine(end, datetime.time.max)
            from_ts = int(start_dt.timestamp())
            to_ts = int(end_dt.timestamp())
            url = (
                "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
                f"?from={from_ts}&to={to_ts}&symbol={symbol.upper()}&resolution=1D"
            )
            r = requests.get(url, headers=DNSE_HEADERS, timeout=15)
            if r.status_code == 200:
                payload = r.json()
                timestamps = payload.get("t", [])
                closes = payload.get("c", [])
                if not timestamps or not closes or len(timestamps) != len(closes):
                    return {}
                result = {}
                for ts, close in zip(timestamps, closes):
                    d = datetime.datetime.fromtimestamp(
                        ts, tz=datetime.timezone.utc
                    ).date()
                    result[d] = parse_float(close)
                return result
        except Exception as e:
            logger.error("source dnse ohlcs %s error: %s", symbol, e)
        return {}

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            end = today()
            start = end - datetime.timedelta(days=14)
            history = self._fetch_ohlcs(asset.symbol, start, end)
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
                "metadata": {"source": "dnse"},
            }
        except Exception as e:
            logger.error("source dnse price %s error: %s", asset.symbol, e)
        return None

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        return self._fetch_ohlcs(symbol, start, end)

    def fetch_listing(self) -> List[dict]:
        return []
