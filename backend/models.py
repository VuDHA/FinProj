import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlmodel import SQLModel, Field, Relationship


def _fk_column(fk_target: str, *, index: bool = False, nullable: bool = False) -> Column:
    """Create a ForeignKey column with ON DELETE CASCADE.

    Works across SQLModel versions (0.0.19 lacks the ondelete= kwarg).
    """
    return Column(
        Integer,
        ForeignKey(fk_target, ondelete="CASCADE"),
        index=index,
        nullable=nullable,
    )


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    name: str
    type: str  # STOCK, FUND, ETF, GOLD, CRYPTO
    exchange: Optional[str] = None
    currency: str = "VND"
    is_active: bool = True
    source: Optional[str] = Field(default=None, index=True)
    source_params: Optional[str] = None  # JSON string for source-specific params


class PriceSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id"))
    date: datetime.date = Field(index=True)
    price: Decimal
    change: Optional[Decimal] = None
    change_percent: Optional[float] = None

    __table_args__ = (
        Index("idx_prices_asset_date", "asset_id", "date", unique=True),
    )


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id"))
    type: str  # BUY, SELL, DEPOSIT, WITHDRAWAL
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    date: datetime.date
    notes: Optional[str] = None

    __table_args__ = (
        Index("idx_transactions_asset_date", "asset_id", "date"),
        Index("idx_transactions_dedup", "asset_id", "type", "quantity", "price", "date", unique=True),
    )


class Income(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id", index=True))
    type: str  # DIVIDEND, INTEREST
    amount: Decimal
    date: datetime.date
    notes: Optional[str] = None


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id"))
    type: str  # STOP_LOSS, TAKE_PROFIT
    value_type: str  # VALUE, PERCENT
    value: Decimal
    reference_price: Optional[Decimal] = None
    is_active: bool = True
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    resolved_at: Optional[datetime.datetime] = None


class AllocationTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True, unique=True)  # STOCK, FUND, ETF, GOLD, CRYPTO
    target_percent: Decimal


class Setting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str


class NewsSource(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    base_url: Optional[str] = None
    source_type: str = Field(default="rss")  # rss, sitemap, html
    feed_url: Optional[str] = None
    config: Optional[str] = None  # JSON string for source-specific params
    is_active: bool = Field(default=True)
    region: str = Field(default="vn")  # vn, global
    last_crawled_at: Optional[datetime.datetime] = None
    fetch_interval_minutes: int = Field(default=30)
    priority: int = Field(default=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class NewsArticle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(sa_column=_fk_column("newssource.id", index=True))
    url: str = Field(index=True)
    title: str
    summary: Optional[str] = None
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None  # comma-separated tags
    published_at: Optional[datetime.datetime] = Field(index=True)
    fetched_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    sentiment_score: Optional[float] = None  # -1.0 to +1.0
    impact_score: Optional[float] = None  # 0.0 to 1.0
    relevance_score: Optional[float] = None  # 0.0 to 1.0
    is_standout: bool = Field(default=False)
    is_active: bool = Field(default=True)
    language: Optional[str] = None  # vi, en, etc.
    region: str = Field(default="vn")

    __table_args__ = (
        Index("idx_articles_published_source", "published_at", "source_id"),
        Index("idx_articles_region_standout_published", "region", "is_standout", "published_at"),
        Index("idx_newsarticle_url_unique", "url", unique=True),
    )


class NewsSymbol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(sa_column=_fk_column("newsarticle.id", index=True))
    symbol: str = Field(index=True)

    __table_args__ = (
        Index("idx_news_symbols_lookup", "symbol", "article_id"),
    )


class Watchlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, unique=True)
    name: Optional[str] = None
    notes: Optional[str] = None
    added_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class NewsAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_type: str = Field(index=True)  # symbol, sentiment, volume, breaking
    symbol: Optional[str] = Field(index=True)
    article_id: int = Field(sa_column=_fk_column("newsarticle.id", index=True))
    title: str
    message: str
    is_read: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ---------------------------------------------------------------------------
# Goal-based savings (Mục tiêu tiết kiệm)
# ---------------------------------------------------------------------------

class Goal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g., "Mua nhà", "Du lịch", "Khẩn cấp"
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    target_date: Optional[str] = None  # ISO date string
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    is_completed: bool = False
    color: Optional[str] = None  # for UI color coding


# ---------------------------------------------------------------------------
# Dividend tracking (Theo dõi cổ tức)
# ---------------------------------------------------------------------------

class Dividend(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id", index=True))
    ex_date: str  # ISO date
    pay_date: Optional[str] = None
    amount_per_share: Decimal
    shares: Decimal  # shares held at ex_date
    total_amount: Decimal  # amount_per_share * shares
    dividend_type: str = "cash"  # "cash" or "stock"
    received: bool = False
    received_at: Optional[str] = None  # timestamp when received, for state machine
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    __table_args__ = (
        Index("idx_dividend_asset_exdate", "asset_id", "ex_date", unique=True),
    )


# ---------------------------------------------------------------------------
# Tax display records (Bản ghi thuế - chỉ hiển thị ước tính)
# ---------------------------------------------------------------------------

class TaxRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tax_year: int = Field(index=True)
    transaction_id: Optional[int] = Field(default=None, sa_column=_fk_column("transaction.id", nullable=True))
    asset_id: Optional[int] = Field(default=None, sa_column=_fk_column("asset.id", index=True, nullable=True))
    tax_type: str  # "capital_gains", "dividend", "transfer_fee"
    taxable_amount: Decimal  # the amount subject to tax
    tax_rate: Decimal  # e.g., 0.1% for transfer, 5% for dividend
    tax_amount: Decimal  # taxable_amount * tax_rate
    is_estimated: bool = True  # always True since this is display-only
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Corporate actions tracking (Theo dõi biến động cổ phiếu)
# ---------------------------------------------------------------------------

class CorporateAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(sa_column=_fk_column("asset.id", index=True))
    action_type: str  # "split", "stock_dividend", "bonus", "rights", "cash_dividend", "par_change"
    ex_date: str  # ISO date
    ratio: Optional[str] = None  # e.g., "2:1" for split, "10:1" for stock dividend
    applied: bool = Field(default=False)  # tracks whether the action has been applied to transactions/prices
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

    __table_args__ = (
        Index("idx_corpaction_asset_exdate_type", "asset_id", "ex_date", "action_type", unique=True),
    )
