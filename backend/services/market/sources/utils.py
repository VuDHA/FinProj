from common.date_utils import (
    parse_date,
    parse_float,
    parse_timestamp_date,
    today,
)


KBS_HEADERS = {
    "Content-Type": "application/json",
    "x-lang": "vi",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://kbsec.com.vn/",
    "Origin": "https://kbsec.com.vn",
}

def cafef_headers() -> dict:
    return {"User-Agent": "Mozilla/5.0"}
