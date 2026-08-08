from decimal import Decimal
from typing import List

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import PortfolioItem, PortfolioSummary
from services.asset_type_config import is_market_price_type, is_total_value_type, shows_pnl_type
from services.market_data import MarketDataService
from services.transaction_types import is_buy_type, is_sell_type


class PortfolioService:
    def __init__(self, session: Session):
        self.session = session
        self.market = MarketDataService(session)

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
            quantity = Decimal("0")
            cost = Decimal("0")
            total_value_mode = is_total_value_type(self.session, asset.type)
            for t in transactions:
                effective_price = self.market.resolve_effective_price(asset, t.date, t.price)
                price = effective_price if effective_price and effective_price > 0 else t.price
                if is_buy_type(t.type):
                    quantity += t.quantity
                    if total_value_mode:
                        # capital = entered value, not quantity × price
                        cost += price + t.fee
                    else:
                        cost += t.quantity * price + t.fee
                elif is_sell_type(t.type):
                    if quantity > 0:
                        avg_cost = cost / quantity
                        cost -= t.quantity * avg_cost
                    quantity -= t.quantity

            if quantity <= 0:
                continue

            held_assets.append(asset)
            holdings[asset.id] = {"quantity": quantity, "cost": cost}

        # Fetch current market prices for held assets automatically.
        market_data: dict[str, dict] = {}
        for quote in self.market.fetch_quotes_for_assets(
            [a for a in held_assets if a.type in ("STOCK", "FUND", "ETF")]
        ):
            market_data[quote["symbol"].upper()] = quote

        for asset in held_assets:
            if asset.type in ("STOCK", "FUND", "ETF"):
                continue
            if not is_market_price_type(self.session, asset.type):
                continue
            data = self.market.fetch_price(asset)
            if data:
                market_data[asset.symbol.upper()] = data

        # Second pass: build portfolio items using the latest available price.
        items: List[PortfolioItem] = []
        total_cost = Decimal("0")
        total_value = Decimal("0")
        market_value = Decimal("0")
        market_cost = Decimal("0")
        stable_value = Decimal("0")

        for asset in held_assets:
            quantity = holdings[asset.id]["quantity"]
            cost = holdings[asset.id]["cost"]
            avg_cost = cost / quantity if quantity > 0 else Decimal("0")

            quote = market_data.get(asset.symbol.upper())
            if quote and (quote.get("price") or 0) > 0:
                self._save_snapshot(asset, quote)

            latest = self.session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
            ).first()
            latest_price = latest.price if latest else avg_cost

            current_value = quantity * latest_price
            pnl = current_value - cost
            pnl_percent = (pnl / cost * 100) if cost else 0.0

            total_cost += cost
            total_value += current_value

            is_market = is_market_price_type(self.session, asset.type)
            shows_pnl = shows_pnl_type(self.session, asset.type)
            if shows_pnl:
                market_value += current_value
                market_cost += cost
            else:
                stable_value += current_value

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

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()

        # PnL is calculated on market-priced assets and non-market assets with
        # showPnl enabled; fixed-capital stable assets are excluded.
        total_pnl = market_value - market_cost
        total_pnl_percent = (total_pnl / market_cost * 100) if market_cost else 0.0

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            market_value=market_value,
            market_cost=market_cost,
            stable_value=stable_value,
            items=items,
        )
