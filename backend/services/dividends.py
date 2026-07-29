"""Business logic for dividend tracking (Theo dõi cổ tức)."""

import datetime
from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, Dividend, Transaction
from schemas import DividendCalendarItem, DividendSummary


def get_dividends_with_asset_info(session: Session, asset_id: Optional[int] = None,
                                  date_from: Optional[str] = None,
                                  date_to: Optional[str] = None) -> List[Dict]:
    """Lấy danh sách cổ tức kèm thông tin asset (symbol, name)."""
    stmt = select(Dividend, Asset).join(Asset, Dividend.asset_id == Asset.id, isouter=True)

    if asset_id is not None:
        stmt = stmt.where(Dividend.asset_id == asset_id)
    if date_from:
        stmt = stmt.where(Dividend.ex_date >= date_from)
    if date_to:
        stmt = stmt.where(Dividend.ex_date <= date_to)

    stmt = stmt.order_by(Dividend.ex_date.desc())
    results = session.exec(stmt).all()

    items = []
    for div, asset in results:
        item = {
            "id": div.id,
            "asset_id": div.asset_id,
            "ex_date": div.ex_date,
            "pay_date": div.pay_date,
            "amount_per_share": div.amount_per_share,
            "shares": div.shares,
            "total_amount": div.total_amount,
            "dividend_type": div.dividend_type,
            "received": div.received,
            "received_at": div.received_at,
            "notes": div.notes,
            "created_at": div.created_at,
            "symbol": asset.symbol if asset else None,
            "asset_name": asset.name if asset else None,
        }
        items.append(item)
    return items


def calculate_total_amount(amount_per_share: Decimal, shares: Decimal) -> Decimal:
    """Tính tổng tiền cổ tức = amount_per_share * shares."""
    return (amount_per_share * shares).quantize(Decimal("0.01"))


def get_dividend_summary(session: Session, asset_id: Optional[int] = None) -> DividendSummary:
    """Tính tổng quan cổ tức: tổng đã nhận, tổng chờ nhận, theo tháng, yield on cost."""
    stmt = select(Dividend)
    if asset_id is not None:
        stmt = stmt.where(Dividend.asset_id == asset_id)
    dividends: List[Dividend] = session.exec(stmt).all()

    total_received = Decimal("0")
    total_pending = Decimal("0")
    monthly: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_asset: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    # Lấy asset info cho by_asset
    asset_map: Dict[int, str] = {}
    if dividends:
        asset_ids = {d.asset_id for d in dividends}
        for asset in session.exec(select(Asset).where(Asset.id.in_(asset_ids))).all():
            asset_map[asset.id] = asset.symbol or asset.name

    for div in dividends:
        amount = div.total_amount
        # Phân loại theo tháng (dựa trên ex_date)
        month_key = div.ex_date[:7] if len(div.ex_date) >= 7 else div.ex_date
        monthly[month_key] += amount

        if div.asset_id in asset_map:
            by_asset[asset_map[div.asset_id]] += amount

        if div.received:
            total_received += amount
        else:
            total_pending += amount

    total_received = total_received.quantize(Decimal("0.01"))
    total_pending = total_pending.quantize(Decimal("0.01"))
    total_all = (total_received + total_pending).quantize(Decimal("0.01"))

    # Tính yield on cost: tổng cổ tức / tổng chi phí đầu tư
    yield_on_cost = None
    txns = session.exec(select(Transaction).where(Transaction.type == "BUY")).all()
    total_cost = sum((t.quantity * t.price + t.fee) for t in txns)
    if total_cost > 0 and total_all > 0:
        yield_on_cost = float(((total_all / total_cost) * Decimal("100")).quantize(Decimal("0.01")))

    # Làm tròn monthly breakdown
    monthly_rounded = {k: v.quantize(Decimal("0.01")) for k, v in sorted(monthly.items())}
    by_asset_rounded = {k: v.quantize(Decimal("0.01")) for k, v in by_asset.items()}

    return DividendSummary(
        total_received=total_received,
        total_pending=total_pending,
        total_all=total_all,
        monthly_breakdown=monthly_rounded,
        yield_on_cost=yield_on_cost,
        by_asset=by_asset_rounded,
    )


def get_dividend_calendar(session: Session, upcoming_only: bool = True) -> List[DividendCalendarItem]:
    """Lấy lịch cổ tức sắp tới (chưa nhận, ex_date >= hôm nay)."""
    stmt = select(Dividend, Asset).join(Asset, Dividend.asset_id == Asset.id, isouter=True)

    if upcoming_only:
        today = datetime.date.today().isoformat()
        stmt = stmt.where(Dividend.ex_date >= today, Dividend.received == False)

    stmt = stmt.order_by(Dividend.ex_date.asc())
    results = session.exec(stmt).all()

    items = []
    for div, asset in results:
        items.append(DividendCalendarItem(
            id=div.id,
            asset_id=div.asset_id,
            symbol=asset.symbol if asset else None,
            asset_name=asset.name if asset else None,
            ex_date=div.ex_date,
            pay_date=div.pay_date,
            amount_per_share=div.amount_per_share,
            shares=div.shares,
            total_amount=div.total_amount,
            dividend_type=div.dividend_type,
            received=div.received,
        ))
    return items
