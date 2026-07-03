from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from common.database import get_session
from common.models import Asset, Transaction
from common.schemas import TransactionCreate, TransactionRead
from common.asset_type_config import is_market_price_type
from services.market.market_data import MarketDataService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def repair_zero_price_transactions(session: Session) -> int:
    """Backfill missing/zero BUY prices for market-priced assets. Returns count repaired."""
    repaired = 0
    txs = session.exec(
        select(Transaction).where(Transaction.type == "BUY", Transaction.price <= 0)
    ).all()
    for tx in txs:
        asset = session.get(Asset, tx.asset_id)
        if not asset or not asset.is_active:
            continue
        if not is_market_price_type(session, asset.type):
            continue
        resolved = MarketDataService(session).resolve_historical_price(asset, tx.date)
        if resolved and resolved > 0:
            tx.price = resolved
            session.add(tx)
            repaired += 1
    if repaired:
        session.commit()
    return repaired

@router.get("/", response_model=List[TransactionRead])
def list_transactions(session: Session = Depends(get_session)):
    return session.exec(select(Transaction).order_by(Transaction.date.desc())).all()


@router.post("/", response_model=TransactionRead)
def create_transaction(
    transaction: TransactionCreate, session: Session = Depends(get_session)
):
    asset = session.get(Asset, transaction.asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    if transaction.type not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Transaction type must be BUY or SELL")

    if transaction.price is None or transaction.price <= 0:
        if is_market_price_type(session, asset.type):
            resolved = MarketDataService(session).resolve_historical_price(asset, transaction.date)
            if resolved is not None:
                transaction.price = resolved

    if transaction.price is None or transaction.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Giá giao dịch không hợp lệ. Vui lòng cung cấp giá hoặc đảm bảo tài sản có dữ liệu thị trường.",
        )

    if transaction.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    if transaction.type == "SELL":
        existing = session.exec(
            select(Transaction)
            .where(Transaction.asset_id == asset.id)
            .order_by(Transaction.date.asc())
        ).all()
        holding = sum(
            t.quantity if t.type == "BUY" else -t.quantity
            for t in existing
            if t.date <= transaction.date
        )
        if transaction.quantity > holding:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sell {transaction.quantity}; holding is {holding}",
            )

    db_tx = Transaction(**transaction.model_dump())
    session.add(db_tx)
    session.commit()
    session.refresh(db_tx)
    return db_tx


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    session.delete(tx)
    session.commit()
    return {"ok": True}
