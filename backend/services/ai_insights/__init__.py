"""AI insight services for portfolio, analytics, market, rebalance, and compare pages."""

from services.ai_insights.analytics import AnalyticsInsightService
from services.ai_insights.compare import CompareInsightService
from services.ai_insights.market import MarketInsightService
from services.ai_insights.portfolio import PortfolioInsightService
from services.ai_insights.rebalance import RebalanceInsightService

__all__ = [
    "AnalyticsInsightService",
    "CompareInsightService",
    "MarketInsightService",
    "PortfolioInsightService",
    "RebalanceInsightService",
]
