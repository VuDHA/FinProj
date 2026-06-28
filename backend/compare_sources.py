import requests, datetime, json

SYMBOLS = ["VCB", "E1VFVN30", "BMF", "FUEVFVND", "SSI"]
HEADERS = {"User-Agent": "Mozilla/5.0"}


def kbs(symbol):
    url = "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stock/iss"
    headers = {
        "Content-Type": "application/json",
        "x-lang": "vi",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://kbsec.com.vn/",
        "Origin": "https://kbsec.com.vn",
    }
    try:
        r = requests.post(url, json={"code": symbol.upper()}, headers=headers, timeout=10)
        if r.status_code == 200 and r.json():
            item = r.json()[0]
            return {
                "price": item.get("CP"),
                "change": item.get("CH"),
                "change_percent": item.get("CHP"),
                "reference": item.get("RE"),
            }
    except Exception as e:
        return {"error": str(e)}
    return None


def cafef_history(symbol):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=14)
    for exchange in ["HOSE", "HNX", "UPCOM"]:
        url = "https://cafef.vn/du-lieu/Ajax/PageNew/DataHistory/PriceHistory.ashx"
        params = {
            "ExchangeType": exchange,
            "Symbol": symbol.upper(),
            "StartDate": start.strftime("%m/%d/%Y"),
            "EndDate": end.strftime("%m/%d/%Y"),
            "PageIndex": 1,
            "PageSize": 5,
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json().get("Data", {}).get("Data", [])
                if data:
                    latest = data[-1]
                    return {
                        "exchange": exchange,
                        "close": latest.get("GiaDongCua"),
                        "change_text": latest.get("ThayDoi"),
                    }
        except Exception as e:
            return {"error": str(e)}
    return None


def ssi_board(symbol):
    url = f"https://iboard-api.ssi.com.vn/stock/exchange"
    params = {"symbol": symbol.upper()}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {"status": r.status_code, "data": data}
    except Exception as e:
        return {"error": str(e)}
    return None


def vndirect_history(symbol):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=14)
    url = "https://finfo-api.vndirect.com.vn/v4/stock_prices/"
    params = {
        "q": f"code:{symbol.upper()}~date:gte:{start.strftime('%Y-%m-%d')}~date:lte:{end.strftime('%Y-%m-%d')}",
        "sort": "date",
        "size": 5,
        "page": 1,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                latest = data[-1]
                return {
                    "close": latest.get("close"),
                    "change": latest.get("change"),
                    "change_pct": latest.get("changePct"),
                    "date": latest.get("date"),
                }
    except Exception as e:
        return {"error": str(e)}
    return None


def main():
    for sym in SYMBOLS:
        print(f"\n=== {sym} ===")
        print("KBS       :", kbs(sym))
        print("CafeF     :", cafef_history(sym))
        print("SSI       :", ssi_board(sym))
        print("VNDirect  :", vndirect_history(sym))


if __name__ == "__main__":
    main()
