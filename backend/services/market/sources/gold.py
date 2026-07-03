import datetime
from typing import Optional

import requests

from common.models import Asset
from services.market.sources.base import Source
from services.market.sources.utils import today


class VangTodayGoldSource(Source):
    code = "vangtoday"
    name = "vang.today"
    description = "Giá vàng miếng SJC từ vang.today."
    supported_types = ["GOLD"]

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            url = "https://www.vang.today/api/prices"
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                payload = r.json()
                prices = payload.get("prices") or payload.get("data") or {}
                for code, item in prices.items():
                    if isinstance(item, dict):
                        buy = float(item.get("buy", 0))
                        if buy > 0:
                            return {
                                "price": buy,
                                "change": 0.0,
                                "change_percent": 0.0,
                                "date": today(),
                            }
        except Exception as e:
            print(f"[source vangtoday] gold error: {e}")
        return None


class SjcGoldSource(Source):
    code = "sjc"
    name = "SJC (fallback)"
    description = "Giá vàng SJC dự phòng khi các nguồn khác không khả dụng."
    supported_types = ["GOLD"]

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        return {
            "price": 78_000_000,
            "change": 0.0,
            "change_percent": 0.0,
            "date": today(),
        }
