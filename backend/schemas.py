import datetime
from typing import Optional, List

from pydantic import BaseModel, model_validator


class AssetCreate(BaseModel):
    symbol: str
    name: str
    type: str
    exchange: Optional[str] = None
    currency: str = "VND"


class AssetRead(AssetCreate):
    id: int
    is_active: bool


class TransactionCreate(BaseModel):
    asset_id: int
    type: str
    quantity: float
    price: float
    fee: float = 0.0
    date: datetime.date
    notes: Optional[str] = None


class TransactionRead(TransactionCreate):
    id: int


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


class MarketSymbol(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str


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
    items: List[PortfolioItem]


class BacktestRequest(BaseModel):
    strategy: str = "buy_and_hold"  # buy_and_hold | rebalancing
    start_date: datetime.date
    end_date: datetime.date
    initial_cash: float = 100_000_000
    rebalance_frequency: str = "monthly"  # monthly | quarterly
    symbols: Optional[List[str]] = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")
        return self


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


class AnalyticsSummary(BaseModel):
    top_performers: List[Performer]
    bottom_performers: List[Performer]
    type_returns: List[TypeReturn]
    monthly_pnl: List[MonthlyPnL]


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
