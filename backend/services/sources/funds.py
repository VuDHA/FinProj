import datetime
from typing import Dict, List, Optional

import requests

from models import Asset
from services.sources.base import Source
from services.sources.utils import parse_float, parse_timestamp_date, today


class FmarketFundSource(Source):
    code = "fmarket"
    name = "Fmarket"
    description = "NAV quỹ mở và danh sách CCQ từ Fmarket."
    supported_types = ["FUND"]
    supports_history = True
    supports_listing = True

    _LISTING_CACHE: Optional[List[dict]] = None
    _LISTING_CACHE_TIME: Optional[datetime.datetime] = None

    def _headers(self) -> dict:
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

    def _fetch_listing(self, force: bool = False) -> List[dict]:
        if (
            not force
            and self._LISTING_CACHE is not None
            and self._LISTING_CACHE_TIME is not None
            and (datetime.datetime.now() - self._LISTING_CACHE_TIME).total_seconds() < 3600
        ):
            return self._LISTING_CACHE
        try:
            url = "https://api.fmarket.vn/res/products/filter"
            all_rows = []
            page = 1
            page_size = 100
            while True:
                payload = {
                    "types": ["NEW_FUND", "TRADING_FUND"],
                    "issuerIds": [],
                    "sortOrder": "DESC",
                    "sortField": "navTo6Months",
                    "page": page,
                    "pageSize": page_size,
                    "isIpo": False,
                    "fundAssetTypes": [],
                    "bondRemainPeriods": [],
                    "searchField": "",
                    "isBuyByReward": False,
                    "thirdAppIds": [],
                }
                r = requests.post(url, json=payload, headers=self._headers(), timeout=15)
                if r.status_code != 200:
                    break
                rows = r.json().get("data", {}).get("rows", [])
                if not rows:
                    break
                all_rows.extend(rows)
                if len(rows) < page_size:
                    break
                page += 1
            if all_rows:
                FmarketFundSource._LISTING_CACHE = all_rows
                FmarketFundSource._LISTING_CACHE_TIME = datetime.datetime.now()
                return all_rows
        except Exception as e:
            print(f"[source fmarket] listing error: {e}")
        return self._LISTING_CACHE or []

    def _find_row(self, symbol: str) -> Optional[dict]:
        listing = self._fetch_listing()
        symbol_upper = symbol.upper()
        return next(
            (
                r
                for r in listing
                if r.get("shortName", "").upper() == symbol_upper
                or r.get("code", "").upper() == symbol_upper
            ),
            None,
        )

    def _fetch_nav_history(
        self,
        fund_id: int,
        start: datetime.date,
        end: datetime.date,
    ) -> List[dict]:
        try:
            url = "https://api.fmarket.vn/res/product/get-nav-history"
            payload = {
                "isAllData": 0,
                "productId": fund_id,
                "fromDate": start.strftime("%Y%m%d"),
                "toDate": end.strftime("%Y%m%d"),
            }
            r = requests.post(url, json=payload, headers=self._headers(), timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if isinstance(data, list):
                    return sorted(data, key=lambda x: x["navDate"])
        except Exception as e:
            print(f"[source fmarket] nav history {fund_id} error: {e}")
        return []

    def fetch_price(self, asset: Asset) -> Optional[dict]:
        try:
            row = self._find_row(asset.symbol)
            if not row:
                return None
            fund_id = row["id"]
            try:
                end = today()
                start = end - datetime.timedelta(days=14)
                nav_history = self._fetch_nav_history(fund_id, start, end)
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
                print(f"[source fmarket] nav {asset.symbol} error: {e}")
            nav = float(row["nav"])
            update_at = row.get("productNavChange", {}).get("updateAt")
            date = parse_timestamp_date(update_at) if update_at else today()
            return {
                "price": nav,
                "change": 0.0,
                "change_percent": 0.0,
                "date": date,
            }
        except Exception as e:
            print(f"[source fmarket] direct {asset.symbol} error: {e}")
            return None

    def fetch_fund_detail(self, symbol: str) -> Optional[dict]:
        try:
            row = self._find_row(symbol)
            if not row:
                return None
            return {
                "symbol": row.get("shortName") or row.get("code"),
                "name": row.get("name"),
                "fund_type": row.get("dataFundAssetType", {}).get("name"),
                "owner": row.get("owner", {}).get("name"),
                "management_fee": row.get("managementFee"),
                "inception_date": parse_timestamp_date(row.get("firstIssueAt")) if row.get("firstIssueAt") else None,
                "nav": float(row.get("nav", 0)),
                "nav_update_at": parse_timestamp_date(row.get("productNavChange", {}).get("updateAt")) if row.get("productNavChange", {}).get("updateAt") else None,
                "vsd_fee_id": row.get("vsdFeeId"),
            }
        except Exception as e:
            print(f"[source fmarket] fund detail {symbol} error: {e}")
            return None

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        try:
            row = self._find_row(symbol)
            if not row:
                return {}
            history = self._fetch_nav_history(row["id"], start, end)
            return {
                datetime.datetime.strptime(h["navDate"], "%Y-%m-%d").date(): float(h["nav"])
                for h in history
            }
        except Exception as e:
            print(f"[source fmarket] history {symbol} error: {e}")
            return {}

    def fetch_listing(self) -> list:
        results = []
        try:
            listing = self._fetch_listing()
            for row in listing:
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
            print(f"[source fmarket] listing error: {e}")
        return results
