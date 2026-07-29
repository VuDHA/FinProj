"""API routes for dividend tracking (Theo dõi cổ tức)."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Asset, Dividend, Transaction
from schemas import (
    DividendCalendarItem,
    DividendCreate,
    DividendRead,
    DividendSummary,
    DividendUpdate,
)
from services.dividends import (
    calculate_total_amount,
    get_dividend_calendar,
    get_dividend_summary,
    get_dividends_with_asset_info,
)
from services.transaction_types import is_buy_type, is_sell_type

router = APIRouter(prefix="/dividends", tags=["dividends"])


@router.get("/", response_model=List[DividendRead])
def list_dividends(
    asset_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """Liệt kê cổ tức, có thể lọc theo asset và khoảng thời gian."""
    return get_dividends_with_asset_info(session, asset_id=asset_id, date_from=date_from, date_to=date_to)


@router.post("/", response_model=DividendRead)
def create_dividend(dividend: DividendCreate, session: Session = Depends(get_session)):
    """Ghi nhận một khoản cổ tức."""
    asset = session.get(Asset, dividend.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if dividend.dividend_type not in ("cash", "stock"):
        raise HTTPException(status_code=400, detail="dividend_type must be 'cash' or 'stock'")
    if dividend.amount_per_share < 0:
        raise HTTPException(status_code=400, detail="amount_per_share must be non-negative")
    if dividend.shares < 0:
        raise HTTPException(status_code=400, detail="shares must be non-negative")

    # NC7: Validate ex_date <= pay_date
    if dividend.pay_date and dividend.pay_date < dividend.ex_date:
        raise HTTPException(status_code=400, detail="pay_date must be on or after ex_date")

    # NC5: Validate shares against actual holdings at ex_date
    ex_date_obj = datetime.date.fromisoformat(dividend.ex_date)
    txns = session.exec(
        select(Transaction).where(
            Transaction.asset_id == dividend.asset_id,
            Transaction.date <= ex_date_obj,
        ).order_by(Transaction.date.asc())
    ).all()
    holding = sum(
        (t.quantity if is_buy_type(t.type) else -t.quantity)
        for t in txns
        if t.date <= ex_date_obj
    )
    if dividend.shares > holding:
        raise HTTPException(
            status_code=400,
            detail=f"Shares ({dividend.shares}) exceeds actual holdings ({holding}) at ex_date",
        )

    payload = dividend.model_dump()
    payload["total_amount"] = calculate_total_amount(dividend.amount_per_share, dividend.shares)

    db_dividend = Dividend(**payload)
    session.add(db_dividend)
    session.commit()
    session.refresh(db_dividend)

    # Trả về kèm thông tin asset
    return DividendRead(
        id=db_dividend.id,
        asset_id=db_dividend.asset_id,
        ex_date=db_dividend.ex_date,
        pay_date=db_dividend.pay_date,
        amount_per_share=db_dividend.amount_per_share,
        shares=db_dividend.shares,
        total_amount=db_dividend.total_amount,
        dividend_type=db_dividend.dividend_type,
        received=db_dividend.received,
        notes=db_dividend.notes,
        created_at=db_dividend.created_at,
        symbol=asset.symbol,
        asset_name=asset.name,
    )


@router.put("/{dividend_id}", response_model=DividendRead)
def update_dividend(dividend_id: int, update: DividendUpdate, session: Session = Depends(get_session)):
    """Cập nhật thông tin cổ tức."""
    div = session.get(Dividend, dividend_id)
    if not div:
        raise HTTPException(status_code=404, detail="Dividend not found")

    # NC6: Validate non-negative amount_per_share and shares
    if update.amount_per_share is not None and update.amount_per_share < 0:
        raise HTTPException(status_code=400, detail="amount_per_share must be non-negative")
    if update.shares is not None and update.shares < 0:
        raise HTTPException(status_code=400, detail="shares must be non-negative")

    if update.ex_date is not None:
        div.ex_date = update.ex_date
    if update.pay_date is not None:
        div.pay_date = update.pay_date

    # NC7: Validate ex_date <= pay_date after applying updates
    effective_ex_date = div.ex_date
    effective_pay_date = div.pay_date
    if effective_pay_date and effective_pay_date < effective_ex_date:
        raise HTTPException(status_code=400, detail="pay_date must be on or after ex_date")

    if update.amount_per_share is not None:
        div.amount_per_share = update.amount_per_share
    if update.shares is not None:
        div.shares = update.shares
    if update.dividend_type is not None:
        if update.dividend_type not in ("cash", "stock"):
            raise HTTPException(status_code=400, detail="dividend_type must be 'cash' or 'stock'")
        div.dividend_type = update.dividend_type

    # NC10: Received toggle — once True, cannot set back to False
    if update.received is not None:
        if update.received and not div.received:
            div.received = True
            div.received_at = datetime.datetime.now().isoformat()
        elif not update.received and div.received:
            raise HTTPException(
                status_code=400,
                detail="Cannot un-receive a dividend that has already been received",
            )

    if update.notes is not None:
        div.notes = update.notes

    # Tính lại total_amount nếu amount_per_share hoặc shares thay đổi
    div.total_amount = calculate_total_amount(div.amount_per_share, div.shares)

    session.add(div)
    session.commit()
    session.refresh(div)

    asset = session.get(Asset, div.asset_id)
    return DividendRead(
        id=div.id,
        asset_id=div.asset_id,
        ex_date=div.ex_date,
        pay_date=div.pay_date,
        amount_per_share=div.amount_per_share,
        shares=div.shares,
        total_amount=div.total_amount,
        dividend_type=div.dividend_type,
        received=div.received,
        notes=div.notes,
        created_at=div.created_at,
        symbol=asset.symbol if asset else None,
        asset_name=asset.name if asset else None,
    )


@router.delete("/{dividend_id}")
def delete_dividend(dividend_id: int, session: Session = Depends(get_session)):
    """Xóa bản ghi cổ tức."""
    div = session.get(Dividend, dividend_id)
    if not div:
        raise HTTPException(status_code=404, detail="Dividend not found")
    session.delete(div)
    session.commit()
    return {"ok": True}


@router.get("/summary", response_model=DividendSummary)
def get_summary(
    asset_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
):
    """Tổng quan cổ tức: theo tháng, yield on cost, tổng đã nhận/chờ nhận."""
    return get_dividend_summary(session, asset_id=asset_id)


@router.get("/calendar", response_model=List[DividendCalendarItem])
def get_calendar(
    upcoming_only: bool = Query(True),
    session: Session = Depends(get_session),
):
    """Lịch cổ tức sắp tới (mặc định: chỉ hiển thị chưa nhận, ex_date >= hôm nay)."""
    return get_dividend_calendar(session, upcoming_only=upcoming_only)
