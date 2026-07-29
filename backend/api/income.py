from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Asset, Income
from schemas import IncomeCreate, IncomeRead

router = APIRouter(prefix="/income", tags=["income"])


@router.get("/", response_model=List[IncomeRead])
def list_income(session: Session = Depends(get_session)):
    return session.exec(select(Income).order_by(Income.date.desc())).all()


@router.post("/", response_model=IncomeRead)
def create_income(income: IncomeCreate, session: Session = Depends(get_session)):
    asset = session.get(Asset, income.asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")
    if income.type not in ("DIVIDEND", "INTEREST"):
        raise HTTPException(status_code=400, detail="Income type must be DIVIDEND or INTEREST")
    if income.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    db_income = Income(**income.model_dump())
    session.add(db_income)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(db_income)
    return db_income


@router.delete("/{income_id}")
def delete_income(income_id: int, session: Session = Depends(get_session)):
    item = session.get(Income, income_id)
    if not item:
        raise HTTPException(status_code=404, detail="Income not found")
    session.delete(item)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"ok": True}
