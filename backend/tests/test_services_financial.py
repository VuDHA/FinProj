import csv
import datetime
import io
from unittest.mock import patch

from models import AllocationTarget, Asset, Income, PriceSnapshot, Transaction
from schemas import BacktestRequest, PortfolioItem, PortfolioSummary
from services.backtest import BacktestService
from services.csv_io import export_assets, export_transactions, import_assets, import_transactions
from services.portfolio import PortfolioService
from services.portfolio_history import PortfolioHistoryService
from services.risk_metrics import RiskMetricsService
from services.analytics import AnalyticsService
from services.rebalance import RebalanceService
from sqlmodel import select


def _create_asset(session, symbol, type="STOCK", name=None):
    asset = Asset(symbol=symbol, name=name or symbol, type=type, currency="VND")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _add_tx(session, asset, type, quantity, price, date, fee=0):
    tx = Transaction(asset_id=asset.id, type=type, quantity=quantity, price=price, fee=fee, date=date)
    session.add(tx)
    session.commit()


def test_export_assets_csv(session):
    _create_asset(session, "VCB", name="Vietcombank")
    csv_text = export_assets(session)
    assert "VCB" in csv_text
    assert "symbol" in csv_text


def test_import_assets_csv(session):
    content = "symbol,name,type,currency\nVNM,Vinamilk,STOCK,VND\n"
    result = import_assets(session, content)
    assert result.created == 1
    assert session.exec(select(Asset).where(Asset.symbol == "VNM")).first() is not None


def test_import_assets_csv_invalid_type(session):
    content = "symbol,name,type,currency\nXYZ,Unknown,INVALID,VND\n"
    result = import_assets(session, content)
    assert result.created == 0
    assert result.errors


def test_export_transactions_csv(session):
    asset = _create_asset(session, "VCB")
    _add_tx(session, asset, "BUY", 10, 100, datetime.date(2023, 1, 1))
    csv_text = export_transactions(session)
    assert "VCB" in csv_text
    assert "BUY" in csv_text


def test_import_transactions_csv(session):
    _create_asset(session, "VCB")
    content = "symbol,type,quantity,price,fee,date,notes\nVCB,BUY,10,100,0,2023-01-01,note\n"
    result = import_transactions(session, content)
    assert result.created == 1


def test_import_transactions_sell_exceeds_holding(session):
    _create_asset(session, "VCB")
    content = "symbol,type,quantity,price,fee,date,notes\nVCB,SELL,10,100,0,2023-01-01,note\n"
    result = import_transactions(session, content)
    assert result.created == 0
    assert result.errors


def test_portfolio_service_with_stock(session, monkeypatch):
    asset = _create_asset(session, "VCB", type="STOCK")
    _add_tx(session, asset, "BUY", 10, 90, datetime.date(2023, 1, 1))
    today = datetime.date.today()

    def fake_quotes(self, assets):
        return [
            {"symbol": a.symbol, "price": 100, "change": 1, "change_percent": 1, "date": today}
            for a in assets
        ]

    monkeypatch.setattr("services.market_data.MarketDataService.fetch_quotes_for_assets", fake_quotes)
    summary = PortfolioService(session).get_portfolio()
    assert summary.total_value == 1000
    assert summary.total_cost == 900
    assert summary.total_pnl == 100
    assert len(summary.items) == 1


def test_portfolio_service_with_gold(session, monkeypatch):
    asset = _create_asset(session, "GOLD", type="GOLD")
    _add_tx(session, asset, "BUY", 1, 70000, datetime.date(2023, 1, 1))
    today = datetime.date.today()

    def fake_price(self, asset):
        return {"price": 75000, "change": 1, "change_percent": 1, "date": today}

    monkeypatch.setattr("services.market_data.MarketDataService.fetch_price", fake_price)
    summary = PortfolioService(session).get_portfolio()
    assert summary.total_value == 75000


def test_portfolio_history_service(session):
    asset = _create_asset(session, "VCB")
    d1 = datetime.date(2023, 1, 1)
    d2 = datetime.date(2023, 1, 2)
    _add_tx(session, asset, "BUY", 10, 90, d1)
    session.add(PriceSnapshot(asset_id=asset.id, date=d1, price=90, change=0, change_percent=0))
    session.add(PriceSnapshot(asset_id=asset.id, date=d2, price=100, change=10, change_percent=11.11))
    session.commit()

    history = PortfolioHistoryService(session).get_history(d1, d2)
    assert len(history) == 2
    assert history[0].value == 900
    assert history[1].value == 1000


def test_portfolio_history_service_uses_avg_cost_fallback_before_first_snapshot(session):
    asset = _create_asset(session, "VCB")
    d_start = datetime.date(2026, 6, 1)
    d_tx = datetime.date(2026, 6, 15)
    d_snapshot = datetime.date(2026, 7, 1)
    d_end = datetime.date(2026, 7, 31)
    _add_tx(session, asset, "BUY", 10, 90, d_tx)
    session.add(PriceSnapshot(asset_id=asset.id, date=d_snapshot, price=100, change=10, change_percent=11.11))
    session.commit()

    history = PortfolioHistoryService(session).get_history(d_start, d_end)
    assert len(history) == (d_end - d_start).days + 1

    # Before the transaction the value is zero.
    idx_tx = (d_tx - d_start).days
    for point in history[:idx_tx]:
        assert point.value == 0.0

    # From the transaction date until the first snapshot, value uses the avg cost fallback.
    idx_snapshot = (d_snapshot - d_start).days
    for point in history[idx_tx:idx_snapshot]:
        assert point.value == 900.0

    # From the snapshot date onwards, value uses the market price.
    for point in history[idx_snapshot:]:
        assert point.value == 1000.0


def test_risk_metrics_service(session, monkeypatch):
    d1 = datetime.date(2023, 1, 1)
    d2 = datetime.date(2023, 2, 1)
    d3 = datetime.date(2023, 3, 1)

    def fake_history(self, start, end):
        from schemas import PortfolioHistoryPoint
        return [
            PortfolioHistoryPoint(date=d1, value=1000, cost=900),
            PortfolioHistoryPoint(date=d2, value=1100, cost=900),
            PortfolioHistoryPoint(date=d3, value=1200, cost=900),
        ]

    def fake_benchmark(self, symbol, start, end):
        from schemas import BenchmarkPoint
        return [
            BenchmarkPoint(date=d1, portfolio_value=1000, benchmark_value=1000),
            BenchmarkPoint(date=d2, portfolio_value=1100, benchmark_value=1050),
            BenchmarkPoint(date=d3, portfolio_value=1200, benchmark_value=1100),
        ]

    monkeypatch.setattr("services.portfolio_history.PortfolioHistoryService.get_history", fake_history)
    monkeypatch.setattr("services.benchmark.BenchmarkService.get_comparison", fake_benchmark)

    metrics = RiskMetricsService(session).get_metrics()
    assert metrics.volatility is not None
    assert metrics.sharpe_ratio is not None
    assert metrics.max_drawdown_percent is not None
    assert metrics.beta is not None


def test_analytics_service(session, monkeypatch):
    from schemas import IncomeSummary

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

    monkeypatch.setattr("services.portfolio.PortfolioService.get_portfolio", fake_portfolio)

    def fake_fetch_history(self, symbol, asset_type, start, end):
        return {}

    monkeypatch.setattr("services.market_data.MarketDataService.fetch_history", fake_fetch_history)

    asset = _create_asset(session, "VCB")
    session.add(Income(asset_id=asset.id, type="DIVIDEND", amount=50, date=datetime.date.today()))
    session.commit()

    summary = AnalyticsService(session).get_summary()
    assert summary.total_income == 50
    assert len(summary.top_performers) == 1
    assert len(summary.type_returns) == 1


def test_rebalance_service(session, monkeypatch):
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

    monkeypatch.setattr("services.portfolio.PortfolioService.get_portfolio", fake_portfolio)
    session.add(AllocationTarget(type="STOCK", target_percent=50))
    session.commit()

    result = RebalanceService(session).suggest()
    assert result.total_value == 1000
    assert len(result.suggestions) == 1
    assert len(result.trades) == 1
    assert result.trades[0].action == "SELL"


def test_backtest_service_buy_and_hold(session, monkeypatch):
    asset = _create_asset(session, "VCB")
    d1 = datetime.date(2023, 1, 1)
    d2 = datetime.date(2023, 1, 2)
    d3 = datetime.date(2023, 1, 3)

    def fake_history(self, symbol, asset_type, start, end):
        return {d1: 100, d2: 110, d3: 120}

    monkeypatch.setattr("services.market_data.MarketDataService.fetch_history", fake_history)
    request = BacktestRequest(
        symbols=["VCB"],
        start_date=d1,
        end_date=d3,
        initial_cash=1000,
        strategy="buy_and_hold",
        rebalance_frequency="monthly",
    )
    result = BacktestService(session).run(request)
    assert result.final_value > 1000
    assert result.total_return_percent > 0


def test_backtest_service_rebalancing(session, monkeypatch):
    asset1 = _create_asset(session, "VCB")
    asset2 = _create_asset(session, "VHM")
    d1 = datetime.date(2023, 1, 1)
    d2 = datetime.date(2023, 2, 1)
    d3 = datetime.date(2023, 3, 1)

    def fake_history(self, symbol, asset_type, start, end):
        prices = {"VCB": {d1: 100, d2: 110, d3: 120}, "VHM": {d1: 100, d2: 100, d3: 100}}
        return prices.get(symbol, {})

    monkeypatch.setattr("services.market_data.MarketDataService.fetch_history", fake_history)
    request = BacktestRequest(
        symbols=["VCB", "VHM"],
        start_date=d1,
        end_date=d3,
        initial_cash=1000,
        strategy="rebalancing",
        rebalance_frequency="monthly",
    )
    result = BacktestService(session).run(request)
    assert result.final_value >= 1000
    assert result.trades
