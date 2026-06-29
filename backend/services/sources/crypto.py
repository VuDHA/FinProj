import datetime
from typing import Optional

import requests

from models import Asset
from services.sources.base import Source
from services.sources.utils import today


class CoinGeckoCryptoSource(Source):
    code = "coingecko"
    name = "CoinGecko"
    description = "Giá crypto và % thay đổi 24h từ CoinGecko."
    supported_types = ["CRYPTO"]

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        mapping = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "BNB": "binancecoin",
        }
        coin_id = mapping.get(asset.symbol.upper(), asset.symbol.lower())
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
                    "date": today(),
                }
        except Exception as e:
            print(f"[source coingecko] {asset.symbol} error: {e}")
        return None
