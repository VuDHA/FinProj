import datetime

from common.models import Asset, PriceSnapshot
from sqlmodel import select


def test_compare_metrics(client, monkeypatch):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=30)
    prices = {start + datetime.timedelta(days=i): 100 + i for i in range(31)}

    def fake_history(self, symbol, asset_type, start, end):
        return prices

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_market_history_with_backfill", fake_history)
    response = client.get(
        "/api/v1/compare/metrics",
        params={"symbols": "VCB", "types": "STOCK", "start": start.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "VCB"
    assert data[0]["total_return"] is not None


def test_compare_correlation(client, monkeypatch):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=30)
    base_prices = {"VCB": 100, "FUEVFVND": 200}

    def fake_history(self, symbol, asset_type, start, end):
        base = base_prices.get(symbol, 100)
        return {start + datetime.timedelta(days=i): base + i for i in range(31)}

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_market_history_with_backfill", fake_history)
    response = client.get(
        "/api/v1/compare/correlation",
        params={
            "symbols": "VCB,FUEVFVND",
            "types": "STOCK,FUND",
            "start": start.isoformat(),
            "end": today.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["labels"] == ["VCB", "FUEVFVND"]
    assert abs(data["matrix"][0][1] - 1.0) < 0.001


def test_compare_too_many_symbols(client):
    today = datetime.date.today()
    response = client.get(
        "/api/v1/compare/metrics",
        params={"symbols": ",".join([f"S{i}" for i in range(10)]), "start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 400


def test_compare_backfills_history(client, session, monkeypatch):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=5)
    prices = {start + datetime.timedelta(days=i): 100 + i for i in range(6)}

    def fake_history(self, symbol, asset_type, start, end):
        return prices

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_market_history", fake_history)
    response = client.get(
        "/api/v1/compare/metrics",
        params={"symbols": "VCB", "types": "STOCK", "start": start.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["total_return"] is not None

    asset = session.exec(select(Asset).where(Asset.symbol == "VCB", Asset.type == "STOCK")).first()
    assert asset is not None
    snapshots = session.exec(select(PriceSnapshot).where(PriceSnapshot.asset_id == asset.id)).all()
    assert len(snapshots) == len(prices)
