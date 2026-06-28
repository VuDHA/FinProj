import datetime
from typing import List, Dict
from collections import defaultdict

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import AnalyticsSummary, Performer, TypeReturn, MonthlyPnL
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
        )

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

        # Last snapshot of each month per asset
        monthly_snapshots: Dict[str, Dict[int, PriceSnapshot]] = defaultdict(dict)
        for asset in assets:
            snapshots = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.asc())
            ).all()
            for s in snapshots:
                month = s.date.strftime("%Y-%m")
                # Keep latest snapshot in the month
                if asset.id not in monthly_snapshots[month] or s.date > monthly_snapshots[month][asset.id].date:
                    monthly_snapshots[month][asset.id] = s

        # Holdings per asset
        holdings: Dict[int, float] = {}
        for asset in assets:
            transactions = self.session.exec(
                select(Transaction).where(Transaction.asset_id == asset.id)
            ).all()
            qty = 0.0
            for t in transactions:
                if t.type == "BUY":
                    qty += t.quantity
                elif t.type == "SELL":
                    qty -= t.quantity
            holdings[asset.id] = qty

        months = sorted(monthly_snapshots.keys())
        result = []
        prev_value = 0.0
        for month in months:
            month_value = 0.0
            for asset_id, snapshot in monthly_snapshots[month].items():
                month_value += snapshot.price * holdings.get(asset_id, 0.0)
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
