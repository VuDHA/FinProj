import re
import xml.etree.ElementTree as ET
from typing import List

import requests

from common.date_utils import parse_number, today
from common.schemas import GoldRate, FxRate, GoldFxResponse


def _fetch_exchangerate_usd_vnd() -> float:
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json().get("rates", {}).get("VND", 0))
    except Exception as e:
        print(f"[gold_fx] exchangerate error: {e}")
    return 0.0


def _fetch_vcb_fx() -> List[FxRate]:
    rates = []

    # Try Vietcombank public XML endpoint first
    try:
        url = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx?b=10"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for ex in root.findall("Exrate"):
                code = ex.attrib.get("CurrencyCode")
                buy = parse_number(ex.attrib.get("Buy", "0"))
                transfer = parse_number(ex.attrib.get("Transfer", "0"))
                sell = parse_number(ex.attrib.get("Sell", "0"))
                if code and (buy or transfer or sell):
                    rates.append(
                        FxRate(
                            currency=f"{code.upper()}/VND",
                            buy=buy,
                            transfer=transfer,
                            sell=sell,
                        )
                    )
            if rates:
                return rates
    except Exception as e:
        print(f"[gold_fx] vcb xml error: {e}")

    # Fallback: scrape VCB public page
    try:
        url = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pListExch.aspx"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            text = r.text
            matches = re.findall(
                r'<tr[^>]*>.*?<td[^>]*>(USD|EUR|JPY|GBP|AUD|CAD|SGD|CHF|CNY|HKD|KRW|THB)</td>.*?'
                r'<td[^>]*>([\d.,]+)</td>.*?<td[^>]*>([\d.,]+)</td>.*?<td[^>]*>([\d.,]+)</td>.*?',
                text,
                re.IGNORECASE | re.DOTALL,
            )
            for currency, buy, transfer, sell in matches:
                rates.append(
                    FxRate(
                        currency=f"{currency.upper()}/VND",
                        buy=parse_number(buy),
                        transfer=parse_number(transfer),
                        sell=parse_number(sell),
                    )
                )
            if rates:
                return rates
    except Exception as e:
        print(f"[gold_fx] vcb scrape error: {e}")

    # Final fallback: exchangerate-api for USD/VND
    usd_vnd = _fetch_exchangerate_usd_vnd()
    if usd_vnd:
        rates.append(
            FxRate(currency="USD/VND", buy=usd_vnd * 0.995, transfer=usd_vnd, sell=usd_vnd * 1.005)
        )

    return rates


def _fetch_gold_sjc() -> List[GoldRate]:
    gold = []
    updated = today().isoformat()

    # vang.today free gold API (no key, CORS enabled)
    try:
        url = "https://www.vang.today/api/prices"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            payload = r.json()
            prices = payload.get("prices") or payload.get("data") or {}
            for code, item in prices.items():
                if isinstance(item, dict):
                    gold.append(
                        GoldRate(
                            source=item.get("name", code),
                            buy=float(item.get("buy", 0)),
                            sell=float(item.get("sell", 0)),
                            updated_at=updated,
                        )
                    )
            if gold:
                return gold
    except Exception as e:
        print(f"[gold_fx] vang.today error: {e}")

    # Fallback placeholder so the app does not crash
    gold.append(
        GoldRate(
            source="SJC (fallback)",
            buy=78_000_000,
            sell=79_000_000,
            updated_at=updated,
        )
    )
    return gold


def get_gold_fx() -> GoldFxResponse:
    return GoldFxResponse(
        gold=_fetch_gold_sjc(),
        fx=_fetch_vcb_fx(),
    )
