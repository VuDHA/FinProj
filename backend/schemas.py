import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AssetSourceInfo(BaseModel):
    code: str
    name: str
    description: str
    supports_history: bool
    supports_listing: bool


class DefaultSourceRequest(BaseModel):
    sources: dict


class AssetTypeConfig(BaseModel):
    label: str
    fields: List[str]
    marketPrice: bool = True


class AssetTypeConfigMap(BaseModel):
    types: Dict[str, AssetTypeConfig]


class AssetCreate(BaseModel):
    symbol: Optional[str] = None
    name: str
    type: str
    exchange: Optional[str] = None
    currency: str = "VND"
    source: Optional[str] = None
    source_params: Optional[str] = None
    manual_value: Optional[float] = None


class AssetRead(AssetCreate):
    id: int
    is_active: bool


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    manual_value: Optional[float] = None


class TransactionCreate(BaseModel):
    asset_id: int
    type: str
    quantity: float
    price: Optional[float] = None
    fee: float = 0.0
    date: datetime.date
    notes: Optional[str] = None


class TransactionRead(TransactionCreate):
    id: int


class TransactionUpdate(BaseModel):
    quantity: Optional[float] = None
    price: Optional[float] = None
    fee: Optional[float] = None
    date: Optional[datetime.date] = None
    notes: Optional[str] = None


class AlertCreate(BaseModel):
    asset_id: int
    type: str  # STOP_LOSS, TAKE_PROFIT
    value_type: str  # VALUE, PERCENT
    value: float


class AlertRead(BaseModel):
    id: int
    asset_id: int
    symbol: Optional[str] = None
    name: Optional[str] = None
    type: str
    value_type: str
    value: float
    reference_price: Optional[float] = None
    is_active: bool
    created_at: Optional[datetime.datetime] = None
    resolved_at: Optional[datetime.datetime] = None


class NotificationRead(BaseModel):
    id: int
    asset_id: int
    symbol: str
    name: str
    type: str
    value_type: str
    value: float
    reference_price: Optional[float] = None
    current_price: float
    message: str


class PriceSnapshotRead(BaseModel):
    id: int
    asset_id: int
    date: datetime.date
    price: float
    change: Optional[float]
    change_percent: Optional[float]


class PriceHistoryPoint(BaseModel):
    date: datetime.date
    price: float


class Quote(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    date: datetime.date
    error: Optional[str] = None


class MarketSymbol(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str
    fund_type: Optional[str] = None


class FundDetail(BaseModel):
    symbol: str
    name: str
    fund_type: Optional[str] = None
    owner: Optional[str] = None
    management_fee: Optional[float] = None
    inception_date: Optional[datetime.date] = None
    nav: float
    nav_update_at: Optional[datetime.date] = None
    vsd_fee_id: Optional[str] = None


class StockDetail(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    price: float
    change: float
    change_percent: float
    date: datetime.date
    pe: Optional[float] = None
    pb: Optional[float] = None
    dividend_yield: Optional[float] = None


class PortfolioItem(BaseModel):
    asset_id: int
    symbol: str
    name: str
    type: str
    quantity: float
    avg_cost: float
    latest_price: float
    current_value: float
    cost: float
    pnl: float
    pnl_percent: float


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_percent: float
    market_value: float
    market_cost: float
    stable_value: float
    items: List[PortfolioItem]


class BacktestRequest(BaseModel):
    strategy: str = "buy_and_hold"  # buy_and_hold | rebalancing
    start_date: datetime.date
    end_date: datetime.date
    initial_cash: float = 100_000_000
    rebalance_frequency: str = "monthly"  # monthly | quarterly
    symbols: Optional[List[str]] = None
    allocations: Optional[Dict[str, float]] = None
    positions: Optional[List["BacktestPosition"]] = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self

    @model_validator(mode="after")
    def check_allocations(self):
        if self.allocations:
            total = sum(self.allocations.values())
            if total > 100:
                raise ValueError("allocations must sum to <= 100")
        return self


class BacktestPosition(BaseModel):
    symbol: str
    price: float
    quantity: float
    ratio: Optional[float] = None  # target allocation in percent


class BacktestPoint(BaseModel):
    date: datetime.date
    value: float


class BacktestTrade(BaseModel):
    date: datetime.date
    symbol: str
    action: str  # BUY | SELL
    quantity: float
    price: float


class BacktestResult(BaseModel):
    final_value: float
    total_return: float
    total_return_percent: float
    max_drawdown_percent: float
    equity_curve: List[BacktestPoint]
    trades: List[BacktestTrade]
    warnings: List[str] = []


class BacktestPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=1000)


class BacktestPromptResponse(BaseModel):
    request: BacktestRequest
    result: BacktestResult


class Performer(BaseModel):
    asset_id: int
    symbol: str
    name: str
    type: str
    pnl: float
    pnl_percent: float


class TypeReturn(BaseModel):
    type: str
    value: float
    cost: float
    pnl: float
    pnl_percent: float


class MonthlyPnL(BaseModel):
    month: str  # YYYY-MM
    start_value: float
    end_value: float
    pnl: float
    pnl_percent: float


class IncomeSummary(BaseModel):
    type: str
    total: float


class PortfolioValueByType(BaseModel):
    type: str
    value: float


class AnalyticsSummary(BaseModel):
    top_performers: List[Performer]
    bottom_performers: List[Performer]
    type_returns: List[TypeReturn]
    monthly_pnl: List[MonthlyPnL]
    income: List[IncomeSummary]
    total_income: float
    total_value: float
    total_cost: float
    stable_value: float
    portfolio_value_by_type: List[PortfolioValueByType]
    filter_type: str
    period_start: str
    period_end: str


class GoldRate(BaseModel):
    source: str
    buy: float
    sell: float
    updated_at: Optional[str] = None


class FxRate(BaseModel):
    currency: str
    buy: float
    transfer: float
    sell: float


class GoldFxResponse(BaseModel):
    gold: List[GoldRate]
    fx: List[FxRate]


class SettingRead(BaseModel):
    id: int
    key: str
    value: str


class SettingCreate(BaseModel):
    key: str
    value: str


class IncomeCreate(BaseModel):
    asset_id: int
    type: str  # DIVIDEND, INTEREST
    amount: float
    date: datetime.date
    notes: Optional[str] = None


class IncomeRead(IncomeCreate):
    id: int


class AllocationTargetCreate(BaseModel):
    type: str
    target_percent: float


class AllocationTargetRead(AllocationTargetCreate):
    id: int


class PortfolioHistoryPoint(BaseModel):
    date: datetime.date
    value: float
    cost: float
    by_type: Dict[str, float] = {}


class BenchmarkPoint(BaseModel):
    date: datetime.date
    portfolio_value: float
    benchmark_value: float


class RebalanceSuggestion(BaseModel):
    type: str
    current_value: float
    current_percent: float
    target_percent: float
    target_value: float
    diff_value: float


class RebalanceTrade(BaseModel):
    symbol: str
    name: str
    action: str  # BUY, SELL
    quantity: float
    estimated_price: float
    estimated_value: float


class RebalanceResult(BaseModel):
    total_value: float
    suggestions: List[RebalanceSuggestion]
    trades: List[RebalanceTrade]


class RiskMetrics(BaseModel):
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    beta: Optional[float] = None


class CsvImportResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]


class SmartImportPreviewResponse(BaseModel):
    filename: str
    sheet_names: Optional[List[str]] = None
    sheet: Optional[str] = None
    headers: List[str]
    sample_rows: List[Dict[str, Any]]
    row_count: int
    suggested_mapping: Dict[str, Optional[str]] = {}


class SmartImportRequest(BaseModel):
    import_type: str = Field(..., pattern="^(assets|transactions)$")
    mapping: Dict[str, Optional[str]]
    sheet: Optional[str] = None


# News module schemas

class ArticleRead(BaseModel):
    id: int
    source_id: int
    source_name: Optional[str] = None
    url: str
    title: str
    summary: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    published_at: Optional[datetime.datetime] = None
    fetched_at: datetime.datetime
    sentiment_score: Optional[float] = None
    impact_score: Optional[float] = None
    relevance_score: Optional[float] = None
    is_standout: bool = False
    language: Optional[str] = None
    region: str = "vn"
    symbols: List[str] = []
    sentiment_label: Optional[str] = None
    impact_label: Optional[str] = None


class ArticleListResponse(BaseModel):
    items: List[ArticleRead]
    total: int
    limit: int
    offset: int


class AlertRead(BaseModel):
    id: int
    alert_type: str
    symbol: Optional[str] = None
    article_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime.datetime


class WatchlistItem(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    notes: Optional[str] = None
    added_at: datetime.datetime


class WatchlistCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    notes: Optional[str] = None


class TrendingSymbol(BaseModel):
    symbol: str
    mentions: int


class TrendingResponse(BaseModel):
    symbols: List[TrendingSymbol]
    sentiment: dict


class DailyBriefResponse(BaseModel):
    generated_at: str
    period_hours: int
    total_articles: int
    top_articles: List[ArticleRead]
    key_symbols: List[TrendingSymbol]


class RefreshResponse(BaseModel):
    results: dict
    alerts_generated: int


class NewsSourceRead(BaseModel):
    id: int
    name: str
    code: str
    region: str = "vn"


class AiSummaryRequest(BaseModel):
    search: Optional[str] = None
    symbol: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern="^(positive|negative|neutral)$")
    min_impact: Optional[float] = Field(None, ge=0, le=1)
    date_from: Optional[datetime.date] = None
    date_to: Optional[datetime.date] = None
    source_id: Optional[int] = None
    tag: Optional[str] = None
    region: Optional[str] = Field("vn", pattern="^(vn|global)$")
    limit: int = Field(20, ge=1, le=50)


class AiSummaryResponse(BaseModel):
    summary: str
    article_count: int
    used_ollama: bool
    personalized: bool = False


class ArticleSummarizeRequest(BaseModel):
    url: str
    title: Optional[str] = None
    language: Optional[str] = "vi"


class ArticleSummarizeResponse(BaseModel):
    summary: str
    tags: List[str]
    source_url: str
    title: Optional[str] = None
    used_ai: bool = False
    partial: bool = False


class ArticleSummarizeTextRequest(BaseModel):
    content_text: str
    title: Optional[str] = None
    language: Optional[str] = "vi"


class CompareMetrics(BaseModel):
    symbol: str
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    sharpe_ratio: Optional[float] = None


class CompareCorrelation(BaseModel):
    labels: List[str]
    matrix: List[List[float]]


# AI insight schemas

class AIInsightResponse(BaseModel):
    overall: str
    details: str
    suggestions: List[str] = []
    used_ollama: bool = False
    cooldown_seconds: int = 0


class PortfolioAIInsightResponse(AIInsightResponse):
    pass


class AnalyticsAIInsightResponse(AIInsightResponse):
    pass


class MarketAIInsightResponse(AIInsightResponse):
    pass


class SymbolAIInsightResponse(AIInsightResponse):
    pass


class RebalanceAIInsightResponse(AIInsightResponse):
    pass


class CompareAIInsightRequest(BaseModel):
    symbols: List[str]
    metrics: List[CompareMetrics]
    correlation: CompareCorrelation


class CompareAIInsightResponse(AIInsightResponse):
    pass


class BacktestStressRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=1000)
    base_request: Optional[BacktestRequest] = None


class BacktestStressResponse(BaseModel):
    request: BacktestRequest
    result: BacktestResult
    used_ollama: bool = False
