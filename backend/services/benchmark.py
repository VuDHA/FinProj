import datetime
from typing import List, Optional

from sqlmodel import Session

from schemas import BenchmarkPoint
from services.market_data import MarketDataService
from services.portfolio_history import PortfolioHistoryService


class BenchmarkService:
    def __init__(self, session: Session):
        self.session = session

    def get_comparison(
        self,
        symbol: str = "VNINDEX",
        start: Optional[datetime.date] = None,
        end: Optional[datetime.date] = None,
    ) -> List[BenchmarkPoint]:
        portfolio_history = PortfolioHistoryService(self.session).get_history(start, end)
        if not portfolio_history:
            return []

        if not start:
            start = portfolio_history[0].date
        if not end:
            end = portfolio_history[-1].date

        market = MarketDataService(self.session)
        benchmark_history = market.fetch_benchmark_history(symbol, start, end)
        if not benchmark_history:
            return []

        # Find the first date where both portfolio value and benchmark price are positive.
        base_date = None
        base_benchmark_price = 0.0
        base_portfolio_value = 0.0
        for point in portfolio_history:
            price = benchmark_history.get(point.date)
            if price is None:
                for d in sorted(benchmark_history.keys()):
                    if d <= point.date:
                        price = benchmark_history[d]
                    else:
                        break
            if price is None or price <= 0 or point.value <= 0:
                continue
            base_date = point.date
            base_benchmark_price = price
            base_portfolio_value = point.value
            break

        if base_date is None or base_benchmark_price <= 0 or base_portfolio_value <= 0:
            return []

        result = []
        for point in portfolio_history:
            if point.date < base_date:
                continue
            price = benchmark_history.get(point.date)
            if price is None:
                for d in sorted(benchmark_history.keys()):
                    if d <= point.date:
                        price = benchmark_history[d]
                    else:
                        break
            if price is None:
                continue
            normalized_benchmark = (price / base_benchmark_price) * base_portfolio_value
            result.append(
                BenchmarkPoint(
                    date=point.date,
                    portfolio_value=round(point.value, 2),
                    benchmark_value=round(normalized_benchmark, 2),
                )
            )
        return result
