import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import PortfolioHistoryPoint


class PortfolioHistoryService:
    def __init__(self, session: Session):
        self.session = session

    def get_history(
        self,
        start: Optional[datetime.date] = None,
        end: Optional[datetime.date] = None,
    ) -> List[PortfolioHistoryPoint]:
        assets = self.session.exec(select(Asset).where(Asset.is_active == True)).all()
        if not assets:
            return []

        # Determine date range from transactions if not provided.
        all_transactions = self.session.exec(
            select(Transaction).order_by(Transaction.date.asc())
        ).all()
        if not all_transactions:
            return []

        if not start:
            start = min(t.date for t in all_transactions)
        if not end:
            end = datetime.date.today()

        if start > end:
            return []

        # Build date range (weekdays only, matching market days loosely).
        dates = self._date_range(start, end)
        if not dates:
            return []

        # Per-asset data.
        asset_transactions: Dict[int, List[Transaction]] = {}
        asset_snapshots: Dict[int, Dict[datetime.date, float]] = {}
        for asset in assets:
            asset_transactions[asset.id] = [
                t for t in all_transactions if t.asset_id == asset.id
            ]
            snaps = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.asc())
            ).all()
            asset_snapshots[asset.id] = {s.date: s.price for s in snaps}

        result = []
        for d in dates:
            day_value = 0.0
            day_cost = 0.0
            day_by_type: Dict[str, float] = {}
            for asset in assets:
                qty = self._quantity_on_date(asset_transactions.get(asset.id, []), d)
                if qty <= 0:
                    continue
                avg_cost = self._avg_cost_on_date(
                    asset_transactions.get(asset.id, []), d
                )
                price = self._latest_price(asset_snapshots.get(asset.id, {}), d)
                if price <= 0:
                    price = avg_cost
                asset_value = qty * price
                asset_cost = qty * avg_cost
                day_value += asset_value
                day_cost += asset_cost
                day_by_type[asset.type] = round(day_by_type.get(asset.type, 0.0) + asset_value, 2)

            result.append(
                PortfolioHistoryPoint(
                    date=d,
                    value=round(day_value, 2),
                    cost=round(day_cost, 2),
                    by_type=day_by_type,
                )
            )

        return result

    @staticmethod
    def _date_range(start: datetime.date, end: datetime.date) -> List[datetime.date]:
        dates = []
        current = start
        while current <= end:
            dates.append(current)
            current += datetime.timedelta(days=1)
        return dates

    @staticmethod
    def _quantity_on_date(transactions: List[Transaction], date: datetime.date) -> float:
        qty = 0.0
        for t in transactions:
            if t.date > date:
                break
            if t.type == "BUY":
                qty += t.quantity
            elif t.type == "SELL":
                qty -= t.quantity
        return qty

    @staticmethod
    def _avg_cost_on_date(transactions: List[Transaction], date: datetime.date) -> float:
        qty = 0.0
        cost = 0.0
        for t in transactions:
            if t.date > date:
                break
            if t.type == "BUY":
                qty += t.quantity
                cost += t.quantity * t.price + t.fee
            elif t.type == "SELL":
                qty -= t.quantity
                cost -= t.quantity * t.price
        if qty <= 0:
            return 0.0
        return cost / qty

    @staticmethod
    def _latest_price(snapshots: Dict[datetime.date, float], date: datetime.date) -> float:
        latest = 0.0
        for d, price in snapshots.items():
            if d <= date and price > 0:
                latest = price
        return latest
