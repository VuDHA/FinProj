import datetime
from unittest.mock import patch

from common.models import Asset, PriceSnapshot
from common.schemas import (
    AnalyticsSummary,
    BenchmarkPoint,
    BacktestResult,
    FundDetail,
    PortfolioItem,
    PortfolioSummary,
    RebalanceResult,
    RebalanceSuggestion,
    RebalanceTrade,
    RiskMetrics,
)


def _create_asset(session, symbol="VCB", type="STOCK"):
    asset = Asset(symbol=symbol, name=symbol, type=type, currency="VND")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def test_refresh_all_prices(client, session, monkeypatch):
    asset = _create_asset(session, symbol="VCB")
    today = datetime.date.today()

    def fake_fetch(self, asset):
        return {"price": 100, "change": 1, "change_percent": 1, "date": today}, []

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_price_with_warnings", fake_fetch)
    response = client.post("/api/v1/prices/refresh-all")
    assert response.status_code == 200
    data = response.json()
    assert data["updated"] == 1
    assert data["failed"] == 0

    snapshot = session.get(PriceSnapshot, 1)
    assert snapshot is not None
    assert snapshot.price == 100


def test_refresh_price(client, session, monkeypatch):
    asset = _create_asset(session, symbol="VCB")
    today = datetime.date.today()

    def fake_fetch(self, asset):
        return {"price": 100, "change": 1, "change_percent": 1, "date": today}, []

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_price_with_warnings", fake_fetch)
    response = client.post(f"/api/v1/prices/refresh/{asset.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["snapshot"]["price"] == 100


def test_refresh_price_not_found(client):
    response = client.post("/api/v1/prices/refresh/999")
    assert response.status_code == 404


def test_refresh_price_fetch_fails(client, session, monkeypatch):
    asset = _create_asset(session, symbol="VCB")

    def fake_fetch(self, asset):
        return None, ["source error"]

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_price_with_warnings", fake_fetch)
    response = client.post(f"/api/v1/prices/refresh/{asset.id}")
    assert response.status_code == 502


def test_get_price_history(client, session, monkeypatch):
    asset = _create_asset(session, symbol="VCB")
    today = datetime.date.today()

    def fake_history(self, symbol, asset_type, start, end):
        return {today: 100}

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_history", fake_history)
    response = client.get(
        f"/api/v1/prices/history/{asset.id}",
        params={"start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price"] == 100


def test_get_quotes(client, monkeypatch):
    today = datetime.date.today()

    def fake_quotes(self, symbols, asset_type="STOCK"):
        return [
            {"symbol": s, "price": 100, "change": 1, "change_percent": 1, "date": today}
            for s in symbols
        ]

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_quotes", fake_quotes)
    response = client.get("/api/v1/prices/quote", params={"symbols": "VCB,VHM", "asset_type": "STOCK"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_symbols(client, monkeypatch):
    def fake_symbols(self):
        return [{"symbol": "VCB", "name": "Vietcombank", "exchange": "HOSE", "type": "STOCK"}]

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_all_symbols", fake_symbols)
    response = client.get("/api/v1/prices/symbols")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_all_stocks(client, monkeypatch):
    def fake_stocks(self):
        return [{"symbol": "VCB", "name": "Vietcombank", "exchange": "HOSE", "type": "STOCK"}]

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_all_stocks", fake_stocks)
    response = client.get("/api/v1/prices/stocks")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_all_funds(client, monkeypatch):
    def fake_funds(self):
        return [{"symbol": "E1VFVN30", "name": "VFM VF1", "exchange": "FUND", "type": "FUND"}]

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_all_funds", fake_funds)
    response = client.get("/api/v1/prices/funds")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_fund_detail(client, monkeypatch):
    def fake_detail(self, symbol):
        return {
            "symbol": symbol,
            "name": "Fund",
            "fund_type": "STOCK",
            "owner": "Owner",
            "management_fee": 1.5,
            "inception_date": "2020-01-01",
            "nav": 100,
            "nav_update_at": "2023-01-01",
            "vsd_fee_id": "id",
        }

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_fund_detail", fake_detail)
    response = client.get("/api/v1/prices/fund-detail/E1VFVN30")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "E1VFVN30"
    assert data["nav"] == 100


def test_get_fund_detail_not_found(client, monkeypatch):
    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_fund_detail", lambda self, symbol: None)
    response = client.get("/api/v1/prices/fund-detail/UNKNOWN")
    assert response.status_code == 404


def test_get_market_history(client, monkeypatch):
    today = datetime.date.today()

    def fake_market_history(self, symbol, type, start, end):
        return {today: 100}

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_market_history_with_backfill", fake_market_history)
    response = client.get(
        "/api/v1/prices/market-history/VCB",
        params={"type": "STOCK", "start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_benchmark(client, monkeypatch):
    today = datetime.date.today()

    def fake_comparison(self, symbol, start, end):
        return [BenchmarkPoint(date=today, portfolio_value=100, benchmark_value=100)]

    monkeypatch.setattr("services.portfolio.benchmark.BenchmarkService.get_comparison", fake_comparison)
    response = client.get(
        "/api/v1/prices/benchmark/VNINDEX",
        params={"start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_benchmark_fails(client, monkeypatch):
    monkeypatch.setattr("services.portfolio.benchmark.BenchmarkService.get_comparison", lambda self, symbol, start, end: [])
    today = datetime.date.today()
    response = client.get(
        "/api/v1/prices/benchmark/VNINDEX",
        params={"start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 502


def test_get_benchmark_raw(client, monkeypatch):
    today = datetime.date.today()

    def fake_benchmark_history(self, symbol, start, end):
        return {today: 100}

    monkeypatch.setattr("services.market.market_data.MarketDataService.fetch_benchmark_history", fake_benchmark_history)
    response = client.get(
        "/api/v1/prices/benchmark-raw/VNINDEX",
        params={"start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_prices_for_asset(client, session):
    asset = _create_asset(session, symbol="VCB")
    today = datetime.date.today()
    session.add(PriceSnapshot(asset_id=asset.id, date=today, price=100, change=1, change_percent=1))
    session.commit()
    response = client.get(f"/api/v1/prices/{asset.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["price"] == 100


def test_get_portfolio(client, monkeypatch):
    def fake_portfolio(self):
        return PortfolioSummary(
            total_value=1000,
            total_cost=900,
            total_pnl=100,
            total_pnl_percent=11.11,
            items=[
                PortfolioItem(
                    asset_id=1,
                    symbol="VCB",
                    name="Vietcombank",
                    type="STOCK",
                    quantity=10,
                    avg_cost=90,
                    latest_price=100,
                    current_value=1000,
                    cost=900,
                    pnl=100,
                    pnl_percent=11.11,
                )
            ],
        )

    monkeypatch.setattr("services.portfolio.portfolio.PortfolioService.get_portfolio", fake_portfolio)
    response = client.get("/api/v1/portfolio/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 1000
    assert len(data["items"]) == 1


def test_get_portfolio_history(client, monkeypatch):
    today = datetime.date.today()

    def fake_history(self, start, end):
        return [{"date": today, "value": 1000, "cost": 900}]

    monkeypatch.setattr("services.portfolio.portfolio_history.PortfolioHistoryService.get_history", fake_history)
    response = client.get(
        "/api/v1/portfolio/history",
        params={"start": today.isoformat(), "end": today.isoformat()},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_analytics(client, monkeypatch):
    def fake_summary(self, filter_type="month", start_date=None, end_date=None):
        return AnalyticsSummary(
            top_performers=[],
            bottom_performers=[],
            type_returns=[],
            monthly_pnl=[],
            income=[],
            total_income=0,
            total_value=0,
            total_cost=0,
            portfolio_value_by_type=[],
            filter_type=filter_type,
            period_start="2023-01-01",
            period_end="2023-01-31",
        )

    monkeypatch.setattr("services.analytics.analytics.AnalyticsService.get_summary", fake_summary)
    response = client.get("/api/v1/analytics/")
    assert response.status_code == 200
    data = response.json()
    assert "total_income" in data


def test_get_risk_metrics(client, monkeypatch):
    def fake_metrics(self):
        return RiskMetrics(volatility=0.1, sharpe_ratio=0.2, max_drawdown_percent=0.3, beta=0.4)

    monkeypatch.setattr("services.portfolio.risk_metrics.RiskMetricsService.get_metrics", fake_metrics)
    response = client.get("/api/v1/analytics/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["volatility"] == 0.1


def test_get_rebalance(client, monkeypatch):
    def fake_suggest(self):
        return RebalanceResult(
            total_value=1000,
            suggestions=[
                RebalanceSuggestion(
                    type="STOCK", current_value=1000, current_percent=100, target_percent=80, target_value=800, diff_value=-200
                )
            ],
            trades=[
                RebalanceTrade(
                    symbol="VCB", name="Vietcombank", action="SELL", quantity=2, estimated_price=100, estimated_value=200
                )
            ],
        )

    monkeypatch.setattr("services.portfolio.rebalance.RebalanceService.suggest", fake_suggest)
    response = client.get("/api/v1/rebalance/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_value"] == 1000


def test_run_backtest(client, monkeypatch):
    def fake_run(self, request):
        return BacktestResult(
            final_value=110000,
            total_return=10000,
            total_return_percent=10,
            max_drawdown_percent=0,
            equity_curve=[],
            trades=[],
            warnings=[],
        )

    monkeypatch.setattr("services.analytics.backtest.BacktestService.run", fake_run)
    response = client.post(
        "/api/v1/backtest/",
        json={
            "strategy": "buy_and_hold",
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",
            "initial_cash": 100000,
            "rebalance_frequency": "monthly",
            "symbols": ["VCB"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["final_value"] == 110000


def test_gold_fx(client, monkeypatch):
    from common.schemas import GoldRate, FxRate

    def fake_gold():
        return [GoldRate(source="test", buy=70000, sell=71000, updated_at="2023-01-01")]

    def fake_fx():
        return [FxRate(currency="USD/VND", buy=23000, transfer=23500, sell=24000)]

    monkeypatch.setattr("services.market.gold_fx._fetch_gold_sjc", fake_gold)
    monkeypatch.setattr("services.market.gold_fx._fetch_vcb_fx", fake_fx)
    response = client.get("/api/v1/gold-fx/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["gold"]) == 1
    assert len(data["fx"]) == 1
