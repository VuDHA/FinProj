import datetime
from typing import Optional, List

from sqlalchemy import Index
from sqlmodel import SQLModel, Field, Relationship


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
    asset_id: int = Field(foreign_key="asset.id")
    date: datetime.date = Field(index=True)
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None

    __table_args__ = (
        Index("idx_prices_asset_date", "asset_id", "date"),
    )


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    type: str  # BUY, SELL, DEPOSIT, WITHDRAWAL
    quantity: float
    price: float
    fee: float = 0.0
    date: datetime.date
    notes: Optional[str] = None

    __table_args__ = (
        Index("idx_transactions_asset_date", "asset_id", "date"),
    )


class Income(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    type: str  # DIVIDEND, INTEREST
    amount: float
    date: datetime.date
    notes: Optional[str] = None


class Alert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    type: str  # STOP_LOSS, TAKE_PROFIT
    value_type: str  # VALUE, PERCENT
    value: float
    reference_price: Optional[float] = None
    is_active: bool = True
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    resolved_at: Optional[datetime.datetime] = None


class AllocationTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True, unique=True)  # STOCK, FUND, ETF, GOLD, CRYPTO
    target_percent: float


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
    source_id: int = Field(foreign_key="newssource.id", index=True)
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
    )


class NewsSymbol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="newsarticle.id", index=True)
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
    article_id: int = Field(foreign_key="newsarticle.id", index=True)
    title: str
    message: str
    is_read: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
