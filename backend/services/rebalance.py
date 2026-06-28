from typing import Dict, List

from sqlmodel import Session, select

from models import AllocationTarget
from schemas import RebalanceResult, RebalanceSuggestion, RebalanceTrade
from services.portfolio import PortfolioService


class RebalanceService:
    def __init__(self, session: Session):
        self.session = session

    def suggest(self) -> RebalanceResult:
        portfolio = PortfolioService(self.session).get_portfolio()
        targets = self.session.exec(select(AllocationTarget)).all()
        target_map: Dict[str, float] = {t.type: t.target_percent for t in targets}

        total_value = portfolio.total_value
        if total_value <= 0:
            return RebalanceResult(total_value=0.0, suggestions=[], trades=[])

        # Group current portfolio by asset type.
        current_by_type: Dict[str, float] = {}
        for item in portfolio.items:
            current_by_type[item.type] = current_by_type.get(item.type, 0.0) + item.current_value

        all_types = set(current_by_type.keys()) | set(target_map.keys())
        suggestions = []
        for t in sorted(all_types):
            current_value = current_by_type.get(t, 0.0)
            current_percent = (current_value / total_value) * 100
            target_percent = target_map.get(t, 0.0)
            target_value = (target_percent / 100) * total_value
            suggestions.append(
                RebalanceSuggestion(
                    type=t,
                    current_value=round(current_value, 2),
                    current_percent=round(current_percent, 2),
                    target_percent=round(target_percent, 2),
                    target_value=round(target_value, 2),
                    diff_value=round(target_value - current_value, 2),
                )
            )

        # Generate per-asset trades for types that need to increase/decrease.
        trades: List[RebalanceTrade] = []
        for suggestion in suggestions:
            if abs(suggestion.diff_value) < 1:
                continue
            # Find assets in this type.
            type_assets = [i for i in portfolio.items if i.type == suggestion.type]
            if suggestion.diff_value > 0:
                # Need to buy. Pick the asset with highest current value to add to.
                target_asset = max(type_assets, key=lambda x: x.latest_price, default=None)
                if not target_asset:
                    continue
                price = target_asset.latest_price
                if price <= 0:
                    continue
                quantity = suggestion.diff_value / price
                trades.append(
                    RebalanceTrade(
                        symbol=target_asset.symbol,
                        name=target_asset.name,
                        action="BUY",
                        quantity=round(quantity, 4),
                        estimated_price=round(price, 2),
                        estimated_value=round(suggestion.diff_value, 2),
                    )
                )
            else:
                # Need to sell. Reduce the largest holding in this type.
                target_asset = max(type_assets, key=lambda x: x.current_value, default=None)
                if not target_asset:
                    continue
                price = target_asset.latest_price
                if price <= 0:
                    continue
                quantity = min(
                    target_asset.quantity,
                    abs(suggestion.diff_value) / price,
                )
                value = quantity * price
                trades.append(
                    RebalanceTrade(
                        symbol=target_asset.symbol,
                        name=target_asset.name,
                        action="SELL",
                        quantity=round(quantity, 4),
                        estimated_price=round(price, 2),
                        estimated_value=round(value, 2),
                    )
                )

        return RebalanceResult(
            total_value=round(total_value, 2),
            suggestions=suggestions,
            trades=trades,
        )
