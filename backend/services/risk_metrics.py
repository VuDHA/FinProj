import datetime
import math
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session

from schemas import RiskMetrics
from services.analytics import AnalyticsService
from services.benchmark import BenchmarkService
from services.portfolio_history import PortfolioHistoryService


class RiskMetricsService:
    # Annualized risk-free rate assumption for Vietnam (~6% per year).
    RISK_FREE_ANNUAL = 0.06

    def __init__(self, session: Session):
        self.session = session

    def get_metrics(self) -> RiskMetrics:
        end = datetime.date.today()
        start = end - datetime.timedelta(days=365)

        portfolio_history = PortfolioHistoryService(self.session).get_history(start, end)
        if len(portfolio_history) < 2:
            return RiskMetrics()

        portfolio_values = {p.date: float(p.value) for p in portfolio_history}

        # Use PnL-based returns (purchases excluded) instead of raw portfolio value changes.
        monthly_pnl = AnalyticsService(self.session)._monthly_pnl(start, end)
        portfolio_monthly = [
            item.pnl_percent / 100 for item in monthly_pnl if item.pnl_percent is not None
        ]
        if len(portfolio_monthly) < 2:
            return RiskMetrics()

        benchmark_data = BenchmarkService(self.session).get_comparison("VNINDEX", start, end)
        benchmark_values = {b.date: float(b.benchmark_value) for b in benchmark_data}
        benchmark_monthly = self._monthly_returns(benchmark_values)

        returns = portfolio_monthly
        volatility = self._annualized_volatility(returns)
        sharpe = self._sharpe_ratio(returns)
        positive_values = {d: v for d, v in portfolio_values.items() if v > 0}
        max_drawdown = self._max_drawdown(positive_values)
        beta = None
        if len(benchmark_monthly) >= 2:
            beta = self._beta(returns, benchmark_monthly)

        return RiskMetrics(
            volatility=round(volatility, 4) if volatility is not None else None,
            sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
            max_drawdown_percent=round(max_drawdown, 2) if max_drawdown is not None else None,
            beta=round(beta, 4) if beta is not None else None,
        )

    @staticmethod
    def _monthly_returns(values: Dict[datetime.date, float]) -> List[float]:
        if not values:
            return []
        # Take last value of each month.
        monthly_values: Dict[str, float] = {}
        for d in sorted(values.keys()):
            month = d.strftime("%Y-%m")
            monthly_values[month] = values[d]
        sorted_months = sorted(monthly_values.keys())

        # Find the first month with a positive value to avoid jumps from zero.
        start_idx = 0
        for i, month in enumerate(sorted_months):
            if monthly_values[month] > 0:
                start_idx = i
                break

        returns = []
        for i in range(start_idx + 1, len(sorted_months)):
            prev = monthly_values[sorted_months[i - 1]]
            curr = monthly_values[sorted_months[i]]
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values)

    @staticmethod
    def _std(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = RiskMetricsService._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def _annualized_volatility(monthly_returns: List[float]) -> Optional[float]:
        if len(monthly_returns) < 2:
            return None
        return RiskMetricsService._std(monthly_returns) * math.sqrt(12)

    @staticmethod
    def _sharpe_ratio(monthly_returns: List[float]) -> Optional[float]:
        if len(monthly_returns) < 2:
            return None
        mean = RiskMetricsService._mean(monthly_returns)
        std = RiskMetricsService._std(monthly_returns)
        if std == 0:
            return None
        monthly_rf = RiskMetricsService.RISK_FREE_ANNUAL / 12
        return ((mean - monthly_rf) / std) * math.sqrt(12)

    @staticmethod
    def _max_drawdown(values: Dict[datetime.date, float]) -> Optional[float]:
        if not values:
            return None
        sorted_values = [values[d] for d in sorted(values.keys())]
        peak = sorted_values[0]
        max_dd = 0.0
        for v in sorted_values:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd * 100

    @staticmethod
    def _beta(portfolio_returns: List[float], benchmark_returns: List[float]) -> Optional[float]:
        # Align lengths (use last N months where N is min length).
        n = min(len(portfolio_returns), len(benchmark_returns))
        if n < 2:
            return None
        p = portfolio_returns[-n:]
        b = benchmark_returns[-n:]
        mean_p = RiskMetricsService._mean(p)
        mean_b = RiskMetricsService._mean(b)
        covariance = sum((p[i] - mean_p) * (b[i] - mean_b) for i in range(n)) / (n - 1)
        variance_b = sum((x - mean_b) ** 2 for x in b) / (n - 1)
        if variance_b == 0:
            return None
        return covariance / variance_b
