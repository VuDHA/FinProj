import datetime
from typing import List, Dict, Optional
from collections import defaultdict

from sqlmodel import Session, select

from models import Asset, Income, PriceSnapshot, Transaction
from schemas import (
    AnalyticsSummary,
    IncomeSummary,
    Performer,
    PortfolioValueByType,
    TypeReturn,
    MonthlyPnL,
)
from services.asset_type_config import is_market_price_type
from services.market_data import MarketDataService
from services.transaction_types import is_buy_type, is_sell_type
from services.portfolio import PortfolioService


class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    def get_summary(
        self,
        filter_type: str = "month",
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> AnalyticsSummary:
        start_date, end_date = self._period_dates(filter_type, start_date, end_date)

        portfolio = PortfolioService(self.session).get_portfolio()

        market_items = [
            item for item in portfolio.items if is_market_price_type(self.session, item.type)
        ]
        items = sorted(market_items, key=lambda x: x.pnl_percent, reverse=True)
        top = items[:5]
        bottom = items[-5:][::-1]

        type_returns = self._type_returns(market_items)
        monthly_pnl = self._monthly_pnl(start_date, end_date)
        income_summary = self._income_summary(start_date, end_date)
        total_value, value_by_type = self._portfolio_value_at_date(end_date)
        total_cost = round(sum(item.cost for item in portfolio.items), 2)

        return AnalyticsSummary(
            top_performers=[
                Performer(
                    asset_id=i.asset_id,
                    symbol=i.symbol,
                    name=i.name,
                    type=i.type,
                    pnl=i.pnl,
                    pnl_percent=i.pnl_percent,
                )
                for i in top
            ],
            bottom_performers=[
                Performer(
                    asset_id=i.asset_id,
                    symbol=i.symbol,
                    name=i.name,
                    type=i.type,
                    pnl=i.pnl,
                    pnl_percent=i.pnl_percent,
                )
                for i in bottom
            ],
            type_returns=type_returns,
            monthly_pnl=monthly_pnl,
            income=income_summary,
            total_income=round(sum(i.total for i in income_summary), 2),
            total_value=round(total_value, 2),
            total_cost=total_cost,
            stable_value=round(portfolio.stable_value, 2),
            portfolio_value_by_type=value_by_type,
            filter_type=filter_type,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
        )

    def _period_dates(
        self,
        filter_type: str,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> tuple[datetime.date, datetime.date]:
        if start_date and end_date:
            return start_date, end_date

        today = datetime.date.today()
        if filter_type == "quarter":
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            end = (
                (start + datetime.timedelta(days=95)).replace(day=1)
                - datetime.timedelta(days=1)
            )
        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
        else:  # month
            start = today.replace(day=1)
            end = (
                (start + datetime.timedelta(days=32)).replace(day=1)
                - datetime.timedelta(days=1)
            )
        return start, end

    def _income_summary(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[IncomeSummary]:
        incomes = self.session.exec(
            select(Income).where(
                Income.date >= start_date, Income.date <= end_date
            )
        ).all()
        grouped: Dict[str, float] = defaultdict(float)
        for income in incomes:
            grouped[income.type] += income.amount
        return [
            IncomeSummary(type=t, total=round(total, 2))
            for t, total in sorted(grouped.items())
        ]

    def _portfolio_value_at_date(
        self, date: datetime.date
    ) -> tuple[float, List[PortfolioValueByType]]:
        assets = self.session.exec(
            select(Asset).where(Asset.is_active == True)
        ).all()
        total = 0.0
        by_type: Dict[str, float] = defaultdict(float)

        for asset in assets:
            transactions = self.session.exec(
                select(Transaction)
                .where(Transaction.asset_id == asset.id)
                .order_by(Transaction.date.asc())
            ).all()
            qty = 0.0
            for t in transactions:
                if t.date > date:
                    break
                if is_buy_type(t.type):
                    qty += t.quantity
                elif is_sell_type(t.type):
                    qty -= t.quantity
            if qty <= 0:
                continue

            snapshot = self.session.exec(
                select(PriceSnapshot)
                .where(
                    PriceSnapshot.asset_id == asset.id,
                    PriceSnapshot.date <= date,
                )
                .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
            ).first()
            if not snapshot or snapshot.price <= 0:
                snapshot = self.session.exec(
                    select(PriceSnapshot)
                    .where(
                        PriceSnapshot.asset_id == asset.id,
                        PriceSnapshot.date >= date,
                    )
                    .order_by(PriceSnapshot.date.asc(), PriceSnapshot.id.asc())
                ).first()
            price = snapshot.price if snapshot and snapshot.price > 0 else 0.0
            value = qty * price
            total += value
            by_type[asset.type] += value

        return total, [
            PortfolioValueByType(type=t, value=round(v, 2))
            for t, v in sorted(by_type.items())
        ]

    def _type_returns(self, items: List) -> List[TypeReturn]:
        grouped = defaultdict(lambda: {"value": 0.0, "cost": 0.0})
        for item in items:
            grouped[item.type]["value"] += item.current_value
            grouped[item.type]["cost"] += item.cost
        result = []
        for t, data in grouped.items():
            pnl = data["value"] - data["cost"]
            pnl_percent = (pnl / data["cost"] * 100) if data["cost"] else 0.0
            result.append(
                TypeReturn(
                    type=t,
                    value=round(data["value"], 2),
                    cost=round(data["cost"], 2),
                    pnl=round(pnl, 2),
                    pnl_percent=round(pnl_percent, 2),
                )
            )
        return sorted(result, key=lambda x: x.pnl_percent, reverse=True)

    def _monthly_pnl(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[MonthlyPnL]:
        assets = self.session.exec(select(Asset).where(Asset.is_active == True)).all()
        assets = [a for a in assets if is_market_price_type(self.session, a.type)]
        if not assets:
            return []

        # Preload transactions per asset, ordered by date
        asset_transactions: Dict[int, List[Transaction]] = {}
        for asset in assets:
            txs = self.session.exec(
                select(Transaction).where(Transaction.asset_id == asset.id).order_by(Transaction.date.asc())
            ).all()
            asset_transactions[asset.id] = txs

        # Generate all month-start dates in the period
        all_months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            all_months.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        # Fetch historical market prices for each asset over the period
        market_data = MarketDataService(self.session)
        asset_prices: Dict[int, Dict[datetime.date, float]] = {}
        for asset in assets:
            try:
                asset_prices[asset.id] = market_data.fetch_history(
                    asset.symbol, asset.type, start_date, end_date
                )
            except Exception as e:
                print(f"[analytics] fetch_history failed for {asset.symbol}: {e}")
                asset_prices[asset.id] = {}

        def _quantity_on_date(asset_id: int, date: datetime.date) -> float:
            qty = 0.0
            for t in asset_transactions.get(asset_id, []):
                if t.date > date:
                    break
                if is_buy_type(t.type):
                    qty += t.quantity
                elif is_sell_type(t.type):
                    qty -= t.quantity
            return qty

        def _price_on_date(prices: Dict[datetime.date, float], date: datetime.date) -> float:
            price = 0.0
            for d, p in sorted(prices.items()):
                if d > date:
                    break
                price = p
            return price

        def _value_at_date(date: datetime.date) -> float:
            total = 0.0
            for asset in assets:
                qty = _quantity_on_date(asset.id, date)
                if qty <= 0:
                    continue
                price = _price_on_date(asset_prices.get(asset.id, {}), date)
                if price <= 0:
                    snapshot = self.session.exec(
                        select(PriceSnapshot)
                        .where(PriceSnapshot.asset_id == asset.id, PriceSnapshot.date <= date)
                        .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
                    ).first()
                    price = snapshot.price if snapshot and snapshot.price > 0 else 0.0
                total += qty * price
            return round(total, 2)

        def _net_investment(start: datetime.date, end: datetime.date) -> float:
            """Net cash injected into the portfolio during (start, end].

            Buy transactions are cash outflows; sell transactions are cash inflows.
            Transactions exactly on the start date are excluded because the
            start portfolio value already includes them.
            """
            market = MarketDataService(self.session)
            buy_cost = 0.0
            sell_proceeds = 0.0
            for asset in assets:
                for t in asset_transactions.get(asset.id, []):
                    if t.date <= start or t.date > end:
                        continue
                    effective_price = market.resolve_effective_price(asset, t.date, t.price)
                    price = effective_price if effective_price and effective_price > 0 else t.price
                    if is_buy_type(t.type):
                        buy_cost += t.quantity * price + t.fee
                    elif is_sell_type(t.type):
                        sell_proceeds += t.quantity * price - t.fee
            return round(buy_cost - sell_proceeds, 2)

        result = []
        prev_value = _value_at_date(start_date)
        for month_start in all_months:
            if month_start.month == 12:
                month_end = datetime.date(month_start.year, month_start.month, 31)
            else:
                month_end = datetime.date(month_start.year, month_start.month + 1, 1) - datetime.timedelta(days=1)
            month_end = min(month_end, end_date)

            month_value = _value_at_date(month_end)
            net_investment = _net_investment(month_start, month_end)
            pnl = round(month_value - prev_value - net_investment, 2)
            invested_capital = round(prev_value + net_investment, 2)
            pnl_percent = round((pnl / invested_capital * 100), 2) if invested_capital > 0 else 0.0
            result.append(
                MonthlyPnL(
                    month=month_start.strftime("%Y-%m"),
                    start_value=round(prev_value, 2),
                    end_value=month_value,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                )
            )
            prev_value = month_value

        return result
