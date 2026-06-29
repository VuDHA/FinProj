import datetime


KBS_HEADERS = {
    "Content-Type": "application/json",
    "x-lang": "vi",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://kbsec.com.vn/",
    "Origin": "https://kbsec.com.vn",
}


def today() -> datetime.date:
    return datetime.datetime.now().date()


def parse_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def parse_date(value) -> datetime.date:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return today()


def parse_timestamp_date(ms: int) -> datetime.date:
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).date()
    except Exception:
        return today()


def cafef_headers() -> dict:
    return {"User-Agent": "Mozilla/5.0"}
