import datetime
import logging
import re
import xml.etree.ElementTree as ET
from typing import List

import requests
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from schemas import GoldRate, FxRate, GoldFxResponse

logger = logging.getLogger(__name__)


def _today() -> datetime.date:
    return datetime.datetime.now().date()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError, Exception)),
    reraise=True,
)
def _fetch_exchangerate_usd_vnd() -> float:
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json().get("rates", {}).get("VND", 0))
    except Exception as e:
        logger.error("gold_fx exchangerate error: %s", e)
    return 0.0


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError, Exception)),
    reraise=True,
)
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
                buy = _parse_number(ex.attrib.get("Buy", "0"))
                transfer = _parse_number(ex.attrib.get("Transfer", "0"))
                sell = _parse_number(ex.attrib.get("Sell", "0"))
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
        logger.error("gold_fx vcb xml error: %s", e)

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
                        buy=_parse_number(buy),
                        transfer=_parse_number(transfer),
                        sell=_parse_number(sell),
                    )
                )
            if rates:
                return rates
    except Exception as e:
        logger.error("gold_fx vcb scrape error: %s", e)

    # Final fallback: exchangerate-api for USD/VND
    usd_vnd = _fetch_exchangerate_usd_vnd()
    if usd_vnd:
        rates.append(
            FxRate(currency="USD/VND", buy=usd_vnd * 0.995, transfer=usd_vnd, sell=usd_vnd * 1.005)
        )

    return rates


def _parse_price_value(raw: str) -> float:
    """Parse a price string that may use comma as decimal or thousands separator."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(" ", "")
    if not s:
        return 0.0
    for sym in ("₫", "$", "€", "£", "¥", "VND", "USD", "EUR"):
        s = s.replace(sym, "")
    s = s.strip()
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        s = s.replace(",", "")
    elif has_comma:
        parts = s.rsplit(",", 1)
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = parts[0].replace(",", "") + "." + parts[1]
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_number(s: str) -> float:
    return _parse_price_value(s)


def _gold_change_percent(change: float, current: float) -> float:
    if not current:
        return 0.0
    previous = current - change
    if not previous:
        return 0.0
    return (change / previous) * 100


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError, Exception)),
    reraise=True,
)
def _fetch_gold_sjc() -> List[GoldRate]:
    gold = []
    updated = _today().isoformat()

    # vang.today free gold API (no key, CORS enabled)
    try:
        url = "https://www.vang.today/api/prices"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            payload = r.json()
            prices = payload.get("prices") or payload.get("data") or {}
            for code, item in prices.items():
                if isinstance(item, dict):
                    buy = float(item.get("buy", 0))
                    change = float(item.get("change_buy", 0))
                    gold.append(
                        GoldRate(
                            source=item.get("name", code),
                            buy=buy,
                            sell=float(item.get("sell", 0)),
                            updated_at=updated,
                            change=change,
                            change_percent=_gold_change_percent(change, buy),
                        )
                    )
            if gold:
                return gold
    except Exception as e:
        logger.error("gold_fx vang.today error: %s", e)

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
