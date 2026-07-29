import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlmodel import Session, select

from database import get_session
from models import Asset, PriceSnapshot, Transaction
from schemas import TransactionCreate, TransactionRead, TransactionUpdate
from services.market_data import MarketDataService
from services.asset_type_config import is_market_price_type
from services.transaction_types import (
    BUY_TYPES,
    is_buy_type,
    is_sell_type,
    MARKET_TRANSACTION_TYPES,
    NON_MARKET_TRANSACTION_TYPES,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def repair_zero_price_transactions(session: Session) -> int:
    """Backfill missing/zero BUY prices for market-priced assets. Returns count repaired."""
    repaired = 0
    market = MarketDataService(session)
    txs = session.exec(
        select(Transaction).where(Transaction.type.in_(list(BUY_TYPES)), Transaction.price <= 0)
    ).all()
    for tx in txs:
        asset = session.get(Asset, tx.asset_id)
        if not asset or not asset.is_active:
            continue
        resolved = market.resolve_effective_price(asset, tx.date, tx.price)
        if resolved and resolved > 0:
            tx.price = resolved
            session.add(tx)
            repaired += 1
    if repaired:
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
    return repaired


@router.get("/", response_model=List[TransactionRead])
def list_transactions(session: Session = Depends(get_session)):
    return session.exec(select(Transaction).order_by(Transaction.date.desc())).all()


def _validate_sell_holding(
    session: Session, asset_id: int, transaction_date: datetime.date, quantity: Decimal, exclude_id: int | None = None
) -> None:
    query = (
        select(Transaction)
        .where(Transaction.asset_id == asset_id)
        .order_by(Transaction.date.asc())
    )
    existing = session.exec(query).all()
    holding = Decimal("0")
    for t in existing:
        if t.date > transaction_date:
            break
        if exclude_id is not None and t.id == exclude_id:
            continue
        if is_buy_type(t.type):
            holding += t.quantity
        elif is_sell_type(t.type):
            holding -= t.quantity
    if quantity > holding:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {quantity}; holding is {holding}",
        )


def _resolve_transaction_price(
    session: Session, asset: Asset, transaction: TransactionCreate | TransactionUpdate
) -> Decimal:
    """Resolve and validate the transaction price, returning a positive Decimal."""
    market = MarketDataService(session)
    price = market.resolve_effective_price(asset, transaction.date, transaction.price)
    if price is None or price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Giá giao dịch không hợp lệ. Vui lòng cung cấp giá hoặc đảm bảo tài sản có dữ liệu thị trường.",
        )
    return price


def _update_stable_snapshot(session: Session, asset: Asset, price: Decimal) -> None:
    """Replace stale snapshots for a non-market asset with the given transaction price."""
    for snap in session.exec(
        select(PriceSnapshot).where(PriceSnapshot.asset_id == asset.id)
    ).all():
        session.delete(snap)
    session.add(
        PriceSnapshot(
            asset_id=asset.id,
            date=datetime.date.today(),
            price=price,
        )
    )


@router.post("/", response_model=TransactionRead)
def create_transaction(
    transaction: TransactionCreate, session: Session = Depends(get_session)
):
    asset = session.get(Asset, transaction.asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    allowed_types = (
        NON_MARKET_TRANSACTION_TYPES
        if not is_market_price_type(session, asset.type)
        else MARKET_TRANSACTION_TYPES
    )
    if transaction.type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Transaction type must be one of {', '.join(sorted(allowed_types))}",
        )

    if transaction.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    if transaction.date > datetime.date.today():
        raise HTTPException(status_code=400, detail="Date cannot be in the future")

    transaction.price = _resolve_transaction_price(session, asset, transaction)

    if is_sell_type(transaction.type):
        # Acquire the write lock before validation so that the validate+insert
        # is atomic and no concurrent write can modify holdings in between.
        session.execute(text("BEGIN IMMEDIATE"))
        _validate_sell_holding(session, asset.id, transaction.date, transaction.quantity)

    db_tx = Transaction(**transaction.model_dump())
    session.add(db_tx)

    # For non-market assets, the transaction price is the latest valuation.
    # Update the snapshot so the dashboard reflects the manual price instead of
    # any stale market price from when the asset was created.
    if not is_market_price_type(session, asset.type):
        _update_stable_snapshot(session, asset, transaction.price)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(db_tx)
    return db_tx


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    update: TransactionUpdate,
    session: Session = Depends(get_session),
):
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    asset = session.get(Asset, tx.asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    if update.quantity is not None and update.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    if update.date is not None and update.date > datetime.date.today():
        raise HTTPException(status_code=400, detail="Date cannot be in the future")

    # Resolve effective price based on the new input price (if any).
    # If the new input is null/0, fall back to market price regardless of the stored price.
    merged_price = update.price
    merged_date = update.date if update.date is not None else tx.date
    effective_price = MarketDataService(session).resolve_effective_price(
        asset, merged_date, merged_price
    )
    if effective_price is None or effective_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Giá giao dịch không hợp lệ. Vui lòng cung cấp giá hoặc đảm bảo tài sản có dữ liệu thị trường.",
        )

    if update.quantity is not None:
        tx.quantity = update.quantity
    if update.price is not None:
        tx.price = update.price
    else:
        # A null price from the client means "use market price".
        tx.price = effective_price
    if update.fee is not None:
        tx.fee = update.fee
    if update.date is not None:
        tx.date = update.date
    if update.notes is not None:
        tx.notes = update.notes
    # Always store the resolved effective price if the final price is null/0.
    if tx.price is None or tx.price <= 0:
        tx.price = effective_price

    if is_sell_type(tx.type):
        # Acquire the write lock before validation so that the validate+insert
        # is atomic and no concurrent write can modify holdings in between.
        session.execute(text("BEGIN IMMEDIATE"))
        _validate_sell_holding(session, asset.id, tx.date, tx.quantity, exclude_id=tx.id)

    session.add(tx)

    # Keep the stable asset snapshot in sync with the latest transaction price.
    if not is_market_price_type(session, asset.type):
        _update_stable_snapshot(session, asset, tx.price)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(tx)
    return tx


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    asset = session.get(Asset, tx.asset_id)
    session.delete(tx)
    session.flush()

    if asset and asset.is_active and not is_market_price_type(session, asset.type):
        latest_tx = session.exec(
            select(Transaction)
            .where(Transaction.asset_id == asset.id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
        ).first()
        if latest_tx:
            _update_stable_snapshot(session, asset, latest_tx.price)
        else:
            for snap in session.exec(
                select(PriceSnapshot).where(PriceSnapshot.asset_id == asset.id)
            ).all():
                session.delete(snap)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"ok": True}
