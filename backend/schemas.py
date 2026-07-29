import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    quantity: Decimal = Field(...)
    price: Optional[Decimal] = None
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    date: datetime.date
    notes: Optional[str] = None


class TransactionRead(TransactionCreate):
    id: int


class TransactionUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fee: Optional[Decimal] = None
    date: Optional[datetime.date] = None
    notes: Optional[str] = None


class AlertCreate(BaseModel):
    asset_id: int
    type: str  # STOP_LOSS, TAKE_PROFIT
    value_type: str  # VALUE, PERCENT
    value: Decimal = Field(..., gt=0)


class AlertRead(BaseModel):
    id: int
    asset_id: int
    symbol: Optional[str] = None
    name: Optional[str] = None
    type: str
    value_type: str
    value: Decimal
    reference_price: Optional[Decimal] = None
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
    value: Decimal
    reference_price: Optional[Decimal] = None
    current_price: Decimal
    message: str


class PriceSnapshotRead(BaseModel):
    id: int
    asset_id: int
    date: datetime.date
    price: Decimal
    change: Optional[Decimal]
    change_percent: Optional[float]


class PriceHistoryPoint(BaseModel):
    date: datetime.date
    price: Decimal


class Quote(BaseModel):
    symbol: str
    price: Decimal
    change: Decimal
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
    management_fee: Optional[Decimal] = None
    inception_date: Optional[datetime.date] = None
    nav: Decimal
    nav_update_at: Optional[datetime.date] = None
    vsd_fee_id: Optional[str] = None


class StockDetail(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    price: Decimal
    change: Decimal
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
    quantity: Decimal
    avg_cost: Decimal
    latest_price: Decimal
    current_value: Decimal
    cost: Decimal
    pnl: Decimal
    pnl_percent: float


class PortfolioSummary(BaseModel):
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_pnl_percent: float
    market_value: Decimal
    market_cost: Decimal
    stable_value: Decimal
    items: List[PortfolioItem]


class BacktestRequest(BaseModel):
    strategy: str = "buy_and_hold"  # buy_and_hold | rebalancing
    start_date: datetime.date
    end_date: datetime.date
    initial_cash: Decimal = Decimal("100000000")
    rebalance_frequency: str = "monthly"  # monthly | quarterly
    symbols: Optional[List[str]] = None
    allocations: Optional[Dict[str, float]] = None
    positions: Optional[List["BacktestPosition"]] = None
    commission_percent: float = Field(default=0.001, ge=0, description="Commission rate as fraction, e.g., 0.001 = 0.1%")
    slippage_percent: float = Field(default=0.0, ge=0, description="Slippage as fraction, e.g., 0.001 = 0.1%")
    execution_lag_days: int = Field(default=1, ge=0, description="Days to wait between signal and execution (1=T+1)")

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
    price: Decimal
    quantity: Decimal
    ratio: Optional[float] = None  # target allocation in percent


class BacktestPoint(BaseModel):
    date: datetime.date
    value: Decimal


class BacktestTrade(BaseModel):
    date: datetime.date
    symbol: str
    action: str  # BUY | SELL
    quantity: Decimal
    price: Decimal


class BacktestResult(BaseModel):
    final_value: Decimal
    total_return: Decimal
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
    pnl: Decimal
    pnl_percent: float


class TypeReturn(BaseModel):
    type: str
    value: Decimal
    cost: Decimal
    pnl: Decimal
    pnl_percent: float


class MonthlyPnL(BaseModel):
    month: str  # YYYY-MM
    start_value: Decimal
    end_value: Decimal
    pnl: Decimal
    pnl_percent: float


class IncomeSummary(BaseModel):
    type: str
    total: Decimal


class PortfolioValueByType(BaseModel):
    type: str
    value: Decimal


class AnalyticsSummary(BaseModel):
    top_performers: List[Performer]
    bottom_performers: List[Performer]
    type_returns: List[TypeReturn]
    monthly_pnl: List[MonthlyPnL]
    income: List[IncomeSummary]
    total_income: Decimal
    total_value: Decimal
    total_cost: Decimal
    stable_value: Decimal
    portfolio_value_by_type: List[PortfolioValueByType]
    filter_type: str
    period_start: str
    period_end: str


class GoldRate(BaseModel):
    source: str
    buy: Decimal
    sell: Decimal
    updated_at: Optional[str] = None
    change: Optional[Decimal] = Decimal("0")
    change_percent: Optional[float] = 0.0


class FxRate(BaseModel):
    currency: str
    buy: Decimal
    transfer: Decimal
    sell: Decimal


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
    amount: Decimal = Field(...)
    date: datetime.date
    notes: Optional[str] = None


class IncomeRead(IncomeCreate):
    id: int


class AllocationTargetCreate(BaseModel):
    type: str
    target_percent: Decimal = Field(..., gt=0, le=100)


class AllocationTargetRead(AllocationTargetCreate):
    id: int


class PortfolioHistoryPoint(BaseModel):
    date: datetime.date
    value: Decimal
    cost: Decimal
    by_type: Dict[str, Decimal] = {}


class BenchmarkPoint(BaseModel):
    date: datetime.date
    portfolio_value: Decimal
    benchmark_value: Decimal


class RebalanceSuggestion(BaseModel):
    type: str
    current_value: Decimal
    current_percent: float
    target_percent: Decimal
    target_value: Decimal
    diff_value: Decimal


class RebalanceTrade(BaseModel):
    symbol: str
    name: str
    action: str  # BUY, SELL
    quantity: Decimal
    estimated_price: Decimal
    estimated_value: Decimal


class RebalanceResult(BaseModel):
    total_value: Decimal
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


# ===========================================================================
# Goal-based savings schemas (Mục tiêu tiết kiệm)
# ===========================================================================

class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal = Field(..., gt=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    target_date: Optional[str] = None  # ISO date string
    color: Optional[str] = None

    @field_validator("target_date")
    @classmethod
    def validate_iso_date(cls, v):
        if v is not None:
            try:
                datetime.date.fromisoformat(v)
            except (ValueError, TypeError):
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class GoalRead(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: Optional[str] = None
    created_at: str
    updated_at: str
    is_completed: bool
    color: Optional[str] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    target_date: Optional[str] = None
    is_completed: Optional[bool] = None
    color: Optional[str] = None

    @field_validator("target_date")
    @classmethod
    def validate_iso_date(cls, v):
        if v is not None:
            try:
                datetime.date.fromisoformat(v)
            except (ValueError, TypeError):
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class GoalContribute(BaseModel):
    amount: Decimal = Field(...)  # can be negative (withdrawal)


class GoalProgress(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    progress_percent: float  # current / target * 100
    remaining: Decimal  # target - current
    is_completed: bool
    target_date: Optional[str] = None


class GoalSummary(BaseModel):
    total_saved: Decimal
    total_target: Decimal
    overall_progress_percent: float
    active_goals: int
    completed_goals: int


# ===========================================================================
# Dividend tracking schemas (Theo dõi cổ tức)
# ===========================================================================

class DividendCreate(BaseModel):
    asset_id: int
    ex_date: str  # ISO date
    pay_date: Optional[str] = None
    amount_per_share: Decimal = Field(..., ge=0)
    shares: Decimal = Field(..., ge=0)
    dividend_type: str = "cash"  # "cash" or "stock"
    received: bool = False
    notes: Optional[str] = None

    @field_validator("ex_date", "pay_date")
    @classmethod
    def validate_iso_date(cls, v):
        if v is not None:
            try:
                datetime.date.fromisoformat(v)
            except (ValueError, TypeError):
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class DividendRead(BaseModel):
    id: int
    asset_id: int
    ex_date: str
    pay_date: Optional[str] = None
    amount_per_share: Decimal
    shares: Decimal
    total_amount: Decimal
    dividend_type: str
    received: bool
    notes: Optional[str] = None
    created_at: str
    symbol: Optional[str] = None  # populated from asset join
    asset_name: Optional[str] = None


class DividendUpdate(BaseModel):
    ex_date: Optional[str] = None
    pay_date: Optional[str] = None
    amount_per_share: Optional[Decimal] = None
    shares: Optional[Decimal] = None
    dividend_type: Optional[str] = None
    received: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("ex_date", "pay_date")
    @classmethod
    def validate_iso_date(cls, v):
        if v is not None:
            try:
                datetime.date.fromisoformat(v)
            except (ValueError, TypeError):
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class DividendSummary(BaseModel):
    total_received: Decimal
    total_pending: Decimal
    total_all: Decimal
    monthly_breakdown: Dict[str, Decimal]  # YYYY-MM -> amount
    yield_on_cost: Optional[float] = None  # total dividends / total cost
    by_asset: Dict[str, Decimal] = {}  # symbol -> total dividends


class DividendCalendarItem(BaseModel):
    id: int
    asset_id: int
    symbol: Optional[str] = None
    asset_name: Optional[str] = None
    ex_date: str
    pay_date: Optional[str] = None
    amount_per_share: Decimal
    shares: Decimal
    total_amount: Decimal
    dividend_type: str
    received: bool


# ===========================================================================
# Tax display schemas (Thuế - chỉ hiển thị ước tính)
# ===========================================================================

class TaxRecordRead(BaseModel):
    id: int
    tax_year: int
    transaction_id: Optional[int] = None
    asset_id: Optional[int] = None
    tax_type: str
    taxable_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    is_estimated: bool
    notes: Optional[str] = None
    created_at: str
    symbol: Optional[str] = None  # populated from asset join


class TaxSummary(BaseModel):
    total_capital_gains_tax: Decimal
    total_dividend_tax: Decimal
    total_transfer_fee: Decimal
    total_tax: Decimal
    record_count: int


class TaxYearSummary(BaseModel):
    tax_year: int
    summary: TaxSummary
    disclaimer: str  # thông báo đây chỉ là ước tính


# ===========================================================================
# Corporate action schemas (Biến động cổ phiếu)
# ===========================================================================

class CorporateActionCreate(BaseModel):
    asset_id: int
    action_type: str  # "split", "stock_dividend", "bonus", "rights", "cash_dividend", "par_change"
    ex_date: str
    ratio: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("ex_date")
    @classmethod
    def validate_iso_date(cls, v):
        if v is not None:
            try:
                datetime.date.fromisoformat(v)
            except (ValueError, TypeError):
                raise ValueError("Date must be in ISO format YYYY-MM-DD")
        return v


class CorporateActionRead(BaseModel):
    id: int
    asset_id: int
    action_type: str
    ex_date: str
    ratio: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    symbol: Optional[str] = None
    asset_name: Optional[str] = None


class PriceAdjustmentResult(BaseModel):
    asset_id: int
    action_type: str
    ratio: Optional[str] = None
    ex_date: str
    prices_adjusted: int
    message: str
