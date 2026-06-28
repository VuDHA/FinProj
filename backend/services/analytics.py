import datetime
from typing import List, Dict
from collections import defaultdict

from sqlmodel import Session, select

from models import Asset, Income, PriceSnapshot, Transaction
from schemas import AnalyticsSummary, IncomeSummary, Performer, TypeReturn, MonthlyPnL
from services.portfolio import PortfolioService


class AnalyticsService:
    def __init__(self, session: Session):
        self.session = session

    def get_summary(self) -> AnalyticsSummary:
        portfolio = PortfolioService(self.session).get_portfolio()

        items = sorted(portfolio.items, key=lambda x: x.pnl_percent, reverse=True)
        top = items[:5]
        bottom = items[-5:][::-1]

        type_returns = self._type_returns(portfolio.items)
        monthly_pnl = self._monthly_pnl()
        income_summary = self._income_summary()

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
        )

    def _income_summary(self) -> List[IncomeSummary]:
        incomes = self.session.exec(select(Income)).all()
        grouped: Dict[str, float] = defaultdict(float)
        for income in incomes:
            grouped[income.type] += income.amount
        return [
            IncomeSummary(type=t, total=round(total, 2))
            for t, total in sorted(grouped.items())
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

    def _monthly_pnl(self) -> List[MonthlyPnL]:
        assets = self.session.exec(select(Asset).where(Asset.is_active == True)).all()
        if not assets:
            return []

        # Latest snapshot per month for each asset
        asset_monthly_snapshots: Dict[int, Dict[str, PriceSnapshot]] = {}
        for asset in assets:
            snapshots = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.asc())
            ).all()
            monthly: Dict[str, PriceSnapshot] = {}
            for s in snapshots:
                month = s.date.strftime("%Y-%m")
                if month not in monthly or s.date > monthly[month].date:
                    monthly[month] = s
            asset_monthly_snapshots[asset.id] = monthly

        # Preload transactions per asset, ordered by date
        asset_transactions: Dict[int, List[Transaction]] = {}
        for asset in assets:
            transactions = self.session.exec(
                select(Transaction)
                .where(Transaction.asset_id == asset.id)
                .order_by(Transaction.date.asc())
            ).all()
            asset_transactions[asset.id] = transactions

        all_months = sorted(
            set().union(*[set(m.keys()) for m in asset_monthly_snapshots.values()])
        )

        result = []
        prev_value = 0.0
        for month in all_months:
            month_value = 0.0
            for asset in assets:
                snapshot = asset_monthly_snapshots.get(asset.id, {}).get(month)
                if not snapshot:
                    continue

                # Holdings as of the snapshot date
                qty = 0.0
                for t in asset_transactions.get(asset.id, []):
                    if t.date > snapshot.date:
                        break
                    if t.type == "BUY":
                        qty += t.quantity
                    elif t.type == "SELL":
                        qty -= t.quantity

                month_value += snapshot.price * qty

            month_value = round(month_value, 2)
            pnl = round(month_value - prev_value, 2) if prev_value else 0.0
            pnl_percent = round((pnl / prev_value * 100), 2) if prev_value else 0.0
            result.append(
                MonthlyPnL(
                    month=month,
                    start_value=round(prev_value, 2),
                    end_value=month_value,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                )
            )
            prev_value = month_value

        return result
