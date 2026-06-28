from typing import List

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import PortfolioItem, PortfolioSummary
from services.market_data import MarketDataService


class PortfolioService:
    def __init__(self, session: Session):
        self.session = session
        self.market = MarketDataService()

    def _save_snapshot(self, asset: Asset, data: dict):
        """Persist a market price snapshot if it is valid and not already stored."""
        if not data or not data.get("price"):
            return
        existing = self.session.exec(
            select(PriceSnapshot).where(
                PriceSnapshot.asset_id == asset.id,
                PriceSnapshot.date == data["date"],
            )
        ).first()
        if existing:
            return
        snapshot = PriceSnapshot(
            asset_id=asset.id,
            date=data["date"],
            price=data["price"],
            change=data.get("change"),
            change_percent=data.get("change_percent"),
        )
        self.session.add(snapshot)

    def get_portfolio(self) -> PortfolioSummary:
        assets = self.session.exec(
            select(Asset).where(Asset.is_active == True)
        ).all()

        # First pass: compute holdings and cost basis for each asset.
        held_assets: List[Asset] = []
        holdings: dict[int, dict] = {}
        for asset in assets:
            transactions = self.session.exec(
                select(Transaction).where(Transaction.asset_id == asset.id)
            ).all()
            quantity = 0.0
            cost = 0.0
            for t in transactions:
                if t.type == "BUY":
                    quantity += t.quantity
                    cost += t.quantity * t.price + t.fee
                elif t.type == "SELL":
                    if quantity > 0:
                        avg_cost = cost / quantity
                        cost -= t.quantity * avg_cost
                        cost += t.fee
                    quantity -= t.quantity

            if quantity <= 0:
                continue

            held_assets.append(asset)
            holdings[asset.id] = {"quantity": quantity, "cost": cost}

        # Fetch current market prices for held assets automatically.
        market_data: dict[str, dict] = {}
        stock_symbols = [
            a.symbol for a in held_assets if a.type in ("STOCK", "FUND", "ETF")
        ]
        if stock_symbols:
            for quote in self.market.fetch_quotes(stock_symbols):
                market_data[quote["symbol"].upper()] = quote

        for asset in held_assets:
            if asset.type in ("STOCK", "FUND", "ETF"):
                continue
            data = self.market.fetch_price(asset)
            if data:
                market_data[asset.symbol.upper()] = data

        # Second pass: build portfolio items using the latest available price.
        items: List[PortfolioItem] = []
        total_cost = 0.0
        total_value = 0.0

        for asset in held_assets:
            quantity = holdings[asset.id]["quantity"]
            cost = holdings[asset.id]["cost"]
            avg_cost = cost / quantity if quantity > 0 else 0.0

            quote = market_data.get(asset.symbol.upper())
            if quote and quote.get("price", 0) > 0:
                self._save_snapshot(asset, quote)

            latest = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.desc())
            ).first()
            latest_price = latest.price if latest else avg_cost

            current_value = quantity * latest_price
            pnl = current_value - cost
            pnl_percent = (pnl / cost * 100) if cost else 0.0

            total_cost += cost
            total_value += current_value

            items.append(
                PortfolioItem(
                    asset_id=asset.id,
                    symbol=asset.symbol,
                    name=asset.name,
                    type=asset.type,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    latest_price=latest_price,
                    current_value=current_value,
                    cost=cost,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                )
            )

        self.session.commit()

        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost else 0.0

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            items=items,
        )
