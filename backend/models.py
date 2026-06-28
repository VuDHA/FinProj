import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import SQLModel, Field


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    name: str
    type: str  # STOCK, FUND, ETF, GOLD, CRYPTO
    exchange: Optional[str] = None
    currency: str = "VND"
    is_active: bool = True


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
    type: str  # BUY, SELL
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


class AllocationTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(index=True, unique=True)  # STOCK, FUND, ETF, GOLD, CRYPTO
    target_percent: float


class Setting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
