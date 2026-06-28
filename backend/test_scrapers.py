from services.market_data import MarketDataService

svc = MarketDataService()

print("=== VCB fetch_quote (KBS live) ===")
print(svc.fetch_quote("VCB"))

print("\n=== BMFF fetch_quote (Fmarket) ===")
print(svc.fetch_quote("BMFF"))

print("\n=== E1VFVN30 fetch_quote (Fmarket miss, KBS live) ===")
print(svc.fetch_quote("E1VFVN30"))

print("\n=== VCB fetch_price (vnstock scrape) ===")
Asset = type('Asset', (), {})
print(svc.fetch_price(type('Asset', (), {'type': 'STOCK', 'symbol': 'VCB'})()))

print("\n=== BMFF fetch_price (Fmarket) ===")
print(svc.fetch_price(type('Asset', (), {'type': 'FUND', 'symbol': 'BMFF'})()))
