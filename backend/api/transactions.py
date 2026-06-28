from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Asset, Transaction
from schemas import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


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

    if transaction.quantity <= 0 or transaction.price < 0:
        raise HTTPException(status_code=400, detail="Quantity and price must be positive")

    if transaction.type == "SELL":
        existing = session.exec(
            select(Transaction).where(Transaction.asset_id == asset.id)
        ).all()
        holding = sum(
            t.quantity if t.type == "BUY" else -t.quantity for t in existing
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
