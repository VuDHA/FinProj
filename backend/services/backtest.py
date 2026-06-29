import datetime
from typing import List, Optional, Dict
from collections import defaultdict

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import BacktestRequest, BacktestPoint, BacktestResult, BacktestTrade
from services.market_data import MarketDataService


class BacktestService:
    def __init__(self, session: Session):
        self.session = session
        self.market = MarketDataService(session)

    def _history_from_public(self, asset: Asset, start: datetime.date, end: datetime.date) -> Dict[datetime.date, float]:
        try:
            return self.market.fetch_history(asset.symbol, asset.type, start, end)
        except Exception as e:
            print(f"[backtest] public history error {asset.symbol}: {e}")
            return {}

    def _history_from_snapshots(self, asset_id: int, start: datetime.date, end: datetime.date) -> Dict[datetime.date, float]:
        snapshots = self.session.exec(
            select(PriceSnapshot)
            .where(
                PriceSnapshot.asset_id == asset_id,
                PriceSnapshot.date >= start,
                PriceSnapshot.date <= end,
            )
            .order_by(PriceSnapshot.date.asc())
        ).all()
        return {s.date: s.price for s in snapshots}

    def _get_history(self, asset: Asset, start: datetime.date, end: datetime.date) -> Dict[datetime.date, float]:
        snapshots = self._history_from_snapshots(asset.id, start, end)
        if len(snapshots) >= 2:
            return snapshots
        if asset.type == "CRYPTO":
            return {}
        return self._history_from_public(asset, start, end)

    def _fill_history(
        self,
        history: Dict[datetime.date, float],
        all_dates: List[datetime.date],
    ) -> Dict[datetime.date, float]:
        """Forward-fill missing prices so every trading day has a value.

        Gaps within the raw date range are filled with the last known price.
        The last known price is also carried forward to the end of the simulation
        so a delisted or thinly-traded asset is not suddenly valued at zero.
        Dates before the first raw price remain absent.
        """
        if not history:
            return {}
        sorted_dates = sorted(history.keys())
        first_date = sorted_dates[0]
        last_date = sorted_dates[-1]
        filled: Dict[datetime.date, float] = {}
        last_price: Optional[float] = None
        for d in sorted(all_dates):
            if d in history:
                last_price = history[d]
            elif d < first_date:
                last_price = None
            elif d > last_date:
                # Extend the last observed price to the end of the simulation.
                # This avoids the asset disappearing from portfolio value on the
                # final dates simply because public data stopped a bit earlier.
                last_price = history[last_date]
            if last_price is not None:
                filled[d] = last_price
        return filled

    def run(self, request: BacktestRequest) -> BacktestResult:
        start = request.start_date
        end = request.end_date

        if start > end:
            raise ValueError("start_date must be before or equal to end_date")

        if request.symbols:
            assets = self.session.exec(
                select(Asset).where(Asset.symbol.in_(request.symbols), Asset.is_active == True)
            ).all()
        else:
            assets = self.session.exec(select(Asset).where(Asset.is_active == True)).all()

        histories_raw: Dict[int, Dict[datetime.date, float]] = {}
        asset_by_id: Dict[int, Asset] = {}
        warnings: List[str] = []

        for asset in assets:
            hist = self._get_history(asset, start, end)
            histories_raw[asset.id] = hist
            asset_by_id[asset.id] = asset
            if not hist:
                warnings.append(f"Không có dữ liệu lịch sử cho {asset.symbol} trong khoảng thời gian đã chọn")

        # Build trading days: union of all dates with price data, sorted
        all_dates = sorted(set().union(*[set(h.keys()) for h in histories_raw.values() if h]))
        if not all_dates:
            return BacktestResult(
                final_value=request.initial_cash,
                total_return=0.0,
                total_return_percent=0.0,
                max_drawdown_percent=0.0,
                equity_curve=[BacktestPoint(date=start, value=request.initial_cash)],
                trades=[],
                warnings=warnings,
            )

        # Forward-fill missing prices for each asset and record warnings
        histories: Dict[int, Dict[datetime.date, float]] = {}
        for asset_id, hist in histories_raw.items():
            if not hist:
                continue
            filled = self._fill_history(hist, all_dates)
            histories[asset_id] = filled
            interpolated = [d for d in filled if d not in hist]
            if interpolated:
                warnings.append(
                    f"Dữ liệu giá của {asset_by_id[asset_id].symbol} đã được nội suy cho {len(interpolated)} ngày thiếu dữ liệu"
                )

        symbols = [asset_by_id[aid].symbol for aid in histories.keys()]
        if not symbols:
            return BacktestResult(
                final_value=request.initial_cash,
                total_return=0.0,
                total_return_percent=0.0,
                max_drawdown_percent=0.0,
                equity_curve=[BacktestPoint(date=start, value=request.initial_cash)],
                trades=[],
                warnings=warnings,
            )

        id_by_symbol = {asset_by_id[aid].symbol: aid for aid in histories.keys()}
        cash = float(request.initial_cash)
        holdings: Dict[str, float] = {symbol: 0.0 for symbol in symbols}
        trades: List[BacktestTrade] = []

        equity_curve: List[BacktestPoint] = []
        max_value = request.initial_cash
        max_drawdown = 0.0

        last_rebalance_date: Optional[datetime.date] = None

        # Buy-and-hold: invest each symbol on the first date it has a price
        first_date_by_symbol = {symbol: min(histories[id_by_symbol[symbol]].keys()) for symbol in symbols}
        symbol_allocation = request.initial_cash / len(symbols)

        for date in all_dates:
            if request.strategy == "rebalancing":
                should_rebalance = False
                if last_rebalance_date is None:
                    should_rebalance = True
                else:
                    delta_months = (date.year - last_rebalance_date.year) * 12 + (date.month - last_rebalance_date.month)
                    if request.rebalance_frequency == "monthly" and delta_months >= 1:
                        should_rebalance = True
                    elif request.rebalance_frequency == "quarterly" and delta_months >= 3:
                        should_rebalance = True

                if should_rebalance:
                    # Only rebalance symbols that have a price on this date
                    available_symbols = [s for s in symbols if date in histories[id_by_symbol[s]]]
                    if available_symbols:
                        current_value = cash + sum(
                            holdings[sym] * histories[id_by_symbol[sym]][date]
                            for sym in available_symbols
                        )
                        target_value_per_symbol = current_value / len(available_symbols)
                        for symbol in available_symbols:
                            asset_id = id_by_symbol[symbol]
                            price = histories[asset_id][date]
                            target_value = target_value_per_symbol
                            current_position_value = holdings[symbol] * price
                            diff_value = target_value - current_position_value
                            if abs(diff_value) > 1:
                                diff_qty = diff_value / price
                                if diff_qty > 0:
                                    cost = diff_qty * price
                                    if cost <= cash + 1:
                                        cash -= cost
                                        holdings[symbol] += diff_qty
                                        trades.append(
                                            BacktestTrade(
                                                date=date,
                                                symbol=symbol,
                                                action="BUY",
                                                quantity=round(diff_qty, 6),
                                                price=round(price, 2),
                                            )
                                        )
                                else:
                                    sell_qty = min(-diff_qty, holdings[symbol])
                                    if sell_qty > 0:
                                        cash += sell_qty * price
                                        holdings[symbol] -= sell_qty
                                        trades.append(
                                            BacktestTrade(
                                                date=date,
                                                symbol=symbol,
                                                action="SELL",
                                                quantity=round(sell_qty, 6),
                                                price=round(price, 2),
                                            )
                                        )
                        last_rebalance_date = date
            else:
                for symbol in symbols:
                    if date == first_date_by_symbol[symbol]:
                        asset_id = id_by_symbol[symbol]
                        price = histories[asset_id][date]
                        if price and price > 0 and cash >= symbol_allocation:
                            qty = symbol_allocation / price
                            cash -= qty * price
                            holdings[symbol] = qty
                            trades.append(
                                BacktestTrade(
                                    date=date,
                                    symbol=symbol,
                                    action="BUY",
                                    quantity=round(qty, 6),
                                    price=round(price, 2),
                                )
                            )

            total_value = cash + sum(
                holdings[sym] * histories[id_by_symbol[sym]].get(date, 0)
                for sym in symbols
            )
            equity_curve.append(BacktestPoint(date=date, value=round(total_value, 2)))
            if total_value > max_value:
                max_value = total_value
            drawdown = (max_value - total_value) / max_value if max_value else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        final_value = equity_curve[-1].value if equity_curve else request.initial_cash
        total_return = final_value - request.initial_cash
        total_return_percent = (total_return / request.initial_cash * 100) if request.initial_cash else 0.0

        return BacktestResult(
            final_value=round(final_value, 2),
            total_return=round(total_return, 2),
            total_return_percent=round(total_return_percent, 2),
            max_drawdown_percent=round(max_drawdown * 100, 2),
            equity_curve=equity_curve,
            trades=trades,
            warnings=warnings,
        )
