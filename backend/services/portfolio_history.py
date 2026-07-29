import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import PortfolioHistoryPoint
from services.market_data import MarketDataService
from services.transaction_types import is_buy_type, is_sell_type


class PortfolioHistoryService:
    def __init__(self, session: Session):
        self.session = session
        self.market = MarketDataService(session)

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
        asset_snapshots: Dict[int, Dict[datetime.date, Decimal]] = {}
        for asset in assets:
            asset_transactions[asset.id] = [
                t for t in all_transactions if t.asset_id == asset.id
            ]
            snaps = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.asc(), PriceSnapshot.id.asc())
            ).all()
            asset_snapshots[asset.id] = {s.date: s.price for s in snaps}

        result = []
        for d in dates:
            day_value = Decimal("0")
            day_cost = Decimal("0")
            day_by_type: Dict[str, Decimal] = {}
            for asset in assets:
                qty = self._quantity_on_date(asset_transactions.get(asset.id, []), d)
                if qty <= 0:
                    continue
                avg_cost = self._avg_cost_on_date(
                    asset_transactions.get(asset.id, []), d, asset
                )
                price = self._latest_price(asset_snapshots.get(asset.id, {}), d)
                if price <= 0:
                    price = avg_cost
                asset_value = qty * price
                asset_cost = qty * avg_cost
                day_value += asset_value
                day_cost += asset_cost
                day_by_type[asset.type] = day_by_type.get(asset.type, Decimal("0")) + asset_value

            result.append(
                PortfolioHistoryPoint(
                    date=d,
                    value=day_value,
                    cost=day_cost,
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
    def _quantity_on_date(transactions: List[Transaction], date: datetime.date) -> Decimal:
        qty = Decimal("0")
        for t in transactions:
            if t.date > date:
                break
            if is_buy_type(t.type):
                qty += t.quantity
            elif is_sell_type(t.type):
                qty -= t.quantity
        return qty

    def _avg_cost_on_date(self, transactions: List[Transaction], date: datetime.date, asset: Asset) -> Decimal:
        qty = Decimal("0")
        cost = Decimal("0")
        for t in transactions:
            if t.date > date:
                break
            effective_price = self.market.resolve_effective_price(asset, t.date, t.price)
            price = effective_price if effective_price and effective_price > 0 else t.price
            if is_buy_type(t.type):
                qty += t.quantity
                cost += t.quantity * price + t.fee
            elif is_sell_type(t.type):
                if qty > 0:
                    avg_cost = cost / qty
                    cost -= t.quantity * avg_cost
                qty -= t.quantity
        if qty <= 0:
            return Decimal("0")
        return cost / qty

    @staticmethod
    def _latest_price(snapshots: Dict[datetime.date, Decimal], date: datetime.date) -> Decimal:
        latest = Decimal("0")
        for d, price in snapshots.items():
            if d <= date and price > 0:
                latest = price
        return latest
