import datetime
import math
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session

from common.schemas import CompareCorrelation, CompareMetrics
from services.market.market_data import MarketDataService

RISK_FREE_ANNUAL = 0.06


def _total_return(values: Dict[datetime.date, float]) -> Optional[float]:
    if not values:
        return None
    sorted_prices = [p for _, p in sorted(values.items())]
    first = sorted_prices[0]
    last = sorted_prices[-1]
    if first <= 0:
        return None
    return (last - first) / first * 100


def _annualized_return(values: Dict[datetime.date, float]) -> Optional[float]:
    if not values or len(values) < 2:
        return None
    sorted_items = sorted(values.items())
    first = sorted_items[0][1]
    last = sorted_items[-1][1]
    if first <= 0:
        return None
    days = (sorted_items[-1][0] - sorted_items[0][0]).days
    if days <= 0:
        return None
    years = days / 365.25
    return ((last / first) ** (1 / years) - 1) * 100


def _log_returns(values: Dict[datetime.date, float]) -> List[float]:
    prices = [p for _, p in sorted(values.items())]
    returns = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        curr = prices[i]
        if prev > 0 and curr > 0:
            returns.append(math.log(curr / prev))
    return returns


def _annualized_volatility(log_returns: List[float]) -> Optional[float]:
    if len(log_returns) < 2:
        return None
    mean = sum(log_returns) / len(log_returns)
    variance = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
    if variance <= 0:
        return None
    return math.sqrt(variance) * math.sqrt(252) * 100


def _max_drawdown(values: Dict[datetime.date, float]) -> Optional[float]:
    peak = 0.0
    max_dd = 0.0
    for _, p in sorted(values.items()):
        if p > peak:
            peak = p
        if peak > 0:
            dd = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100 if max_dd > 0 else None


def _sharpe_ratio(annualized_return: float, volatility: float) -> Optional[float]:
    if volatility == 0:
        return None
    return (annualized_return - RISK_FREE_ANNUAL * 100) / volatility


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


class CompareService:
    def __init__(self, session: Session):
        self.session = session
        self.market = MarketDataService(session)

    def fetch_histories(
        self,
        symbols: List[Tuple[str, str]],
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[str, Dict[datetime.date, float]]:
        result: Dict[str, Dict[datetime.date, float]] = {}
        for symbol, asset_type in symbols:
            try:
                history = self.market.fetch_market_history_with_backfill(symbol, asset_type, start, end)
                result[symbol.upper()] = history or {}
            except Exception as e:
                print(f"[compare] history {symbol} error: {e}")
                result[symbol.upper()] = {}
        return result

    def metrics(
        self,
        symbols: List[Tuple[str, str]],
        start: datetime.date,
        end: datetime.date,
    ) -> List[CompareMetrics]:
        histories = self.fetch_histories(symbols, start, end)
        out = []
        for symbol, _ in symbols:
            values = histories.get(symbol.upper(), {})
            if not values:
                out.append(CompareMetrics(symbol=symbol.upper()))
                continue

            total = _total_return(values)
            ann = _annualized_return(values)
            log_rets = _log_returns(values)
            vol = _annualized_volatility(log_rets)
            dd = _max_drawdown(values)
            sharpe = None
            if ann is not None and vol is not None and vol > 0:
                sharpe = _sharpe_ratio(ann, vol)

            out.append(
                CompareMetrics(
                    symbol=symbol.upper(),
                    total_return=round(total, 2) if total is not None else None,
                    annualized_return=round(ann, 2) if ann is not None else None,
                    volatility=round(vol, 2) if vol is not None else None,
                    max_drawdown_percent=round(dd, 2) if dd is not None else None,
                    sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
                )
            )
        return out

    def correlation(
        self,
        symbols: List[Tuple[str, str]],
        start: datetime.date,
        end: datetime.date,
    ) -> CompareCorrelation:
        histories = self.fetch_histories(symbols, start, end)
        labels = [symbol.upper() for symbol, _ in symbols]

        return_series: Dict[str, Dict[datetime.date, float]] = {}
        for symbol, _ in symbols:
            values = histories.get(symbol.upper(), {})
            if not values:
                continue
            sorted_items = sorted(values.items())
            rets = {}
            for i in range(1, len(sorted_items)):
                prev_date, prev_price = sorted_items[i - 1]
                curr_date, curr_price = sorted_items[i]
                if prev_price > 0:
                    rets[curr_date] = (curr_price - prev_price) / prev_price
            return_series[symbol.upper()] = rets

        common_dates = None
        for rets in return_series.values():
            dates = set(rets.keys())
            common_dates = dates if common_dates is None else common_dates & dates

        if not common_dates or len(common_dates) < 2:
            return CompareCorrelation(
                labels=labels, matrix=[[0.0] * len(labels) for _ in labels]
            )

        n = len(labels)
        matrix = [[0.0] * n for _ in range(n)]
        sorted_dates = sorted(common_dates)
        for i, sym_i in enumerate(labels):
            for j, sym_j in enumerate(labels):
                if i == j:
                    matrix[i][j] = 1.0
                    continue
                if sym_i not in return_series or sym_j not in return_series:
                    matrix[i][j] = 0.0
                    continue
                xs = [return_series[sym_i][d] for d in sorted_dates]
                ys = [return_series[sym_j][d] for d in sorted_dates]
                matrix[i][j] = round(_pearson(xs, ys), 4)
        return CompareCorrelation(labels=labels, matrix=matrix)
