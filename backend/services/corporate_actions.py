"""Business logic for corporate actions tracking (Theo dõi biến động cổ phiếu).

Hỗ trợ các loại biến động:
- split: Tách cổ phiếu (ví dụ 2:1)
- stock_dividend: Cổ tức bằng cổ phiếu (ví dụ 10:1)
- bonus: Phát hành cổ phiếu thưởng
- rights: Phát hành quyền mua
- cash_dividend: Cổ tức tiền mặt
- par_change: Thay đổi mệnh giá
"""

import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select

from models import CorporateAction, PriceSnapshot, Transaction


def parse_ratio(ratio: str) -> Tuple[float, float]:
    """Phân tích chuỗi tỷ lệ, ví dụ "2:1" -> (2.0, 1.0).

    Ý nghĩa: với split 2:1, mỗi 1 cổ phiếu cũ thành 2 cổ phiếu mới.
    Raises ValueError on invalid input instead of silently returning 1:1.
    """
    if not ratio:
        raise ValueError("Ratio is required")
    parts = ratio.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid ratio format: {ratio}. Expected 'new:old', e.g., '2:1'")
    try:
        new = float(parts[0].strip())
        old = float(parts[1].strip())
        if old == 0:
            raise ValueError("Ratio denominator cannot be zero")
        if new <= 0 or old <= 0:
            raise ValueError("Ratio values must be positive")
        return (new, old)
    except ValueError as e:
        if "Ratio" in str(e):
            raise
        raise ValueError(f"Invalid ratio values: {ratio}")


def get_adjustment_factor(action_type: str, ratio: str) -> float:
    """Tính hệ số điều chỉnh giá lịch sử cho một biến động.

    - split 2:1 -> giá cũ chia 2 (factor = 1/2 = 0.5)
    - stock_dividend 10:1 -> nhận thêm 1 cổ cho mỗi 10 cổ -> factor = 10/11
    - bonus 10:1 -> tương tự stock_dividend
    - cash_dividend -> giảm giá theo mức cổ tức (không điều chỉnh ở đây)
    - par_change -> theo tỷ lệ thay đổi mệnh giá
    """
    new, old = parse_ratio(ratio)

    if action_type in ("split",):
        # split 2:1: 1 cổ cũ -> 2 cổ mới, giá cũ = giá mới * 2
        # factor để nhân với giá cũ: old/new = 1/2
        return old / new if new > 0 else 1.0

    if action_type in ("stock_dividend", "bonus"):
        # stock_dividend 10:1: mỗi 10 cổ nhận thêm 1 cổ
        # tổng cổ sau = old + new, giá cũ = giá mới * (old + new) / old
        # factor = old / (old + new)
        total = old + new
        return old / total if total > 0 else 1.0

    if action_type in ("rights",):
        # Rights issue phức tạp hơn, tạm thời không điều chỉnh giá
        return 1.0

    if action_type in ("par_change",):
        # Thay đổi mệnh giá theo tỷ lệ
        return old / new if new > 0 else 1.0

    if action_type in ("cash_dividend",):
        # Cash dividend không điều chỉnh giá lịch sử trong module này
        return 1.0

    return 1.0


def get_transaction_factors(action_type: str, ratio: str) -> Tuple[Decimal, Decimal]:
    """Tính hệ số điều chỉnh giao dịch (quantity_factor, price_factor).

    - quantity_factor: nhân với quantity cũ để ra quantity mới
    - price_factor: nhân với price cũ để ra price mới (giá giảm khi số cổ tăng)

    For split 2:1:  qty_factor = 2/1 = 2,  price_factor = 1/2 = 0.5
    For stock_dividend 10:1 (10% bonus):  qty_factor = 11/10,  price_factor = 10/11
    For reverse split 1:2:  qty_factor = 1/2 = 0.5,  price_factor = 2/1 = 2
    """
    new, old = parse_ratio(ratio)

    if action_type in ("split", "par_change"):
        qty_factor = Decimal(str(new)) / Decimal(str(old))
        price_factor = Decimal(str(old)) / Decimal(str(new))
    elif action_type in ("stock_dividend", "bonus"):
        total = old + new
        qty_factor = Decimal(str(total)) / Decimal(str(old))
        price_factor = Decimal(str(old)) / Decimal(str(total))
    else:
        # rights, cash_dividend — no transaction adjustment
        qty_factor = Decimal("1")
        price_factor = Decimal("1")

    return qty_factor, price_factor


def record_corporate_action(
    session: Session,
    asset_id: int,
    action_type: str,
    ex_date: str,
    ratio: Optional[str] = None,
    notes: Optional[str] = None,
) -> CorporateAction:
    """Ghi nhận một sự kiện biến động cổ phiếu."""
    valid_types = {"split", "stock_dividend", "bonus", "rights", "cash_dividend", "par_change"}
    if action_type not in valid_types:
        raise ValueError(
            f"action_type must be one of {', '.join(sorted(valid_types))}"
        )

    action = CorporateAction(
        asset_id=asset_id,
        action_type=action_type,
        ex_date=ex_date,
        ratio=ratio,
        notes=notes,
    )
    session.add(action)
    session.commit()
    session.refresh(action)
    return action


def apply_corporate_action(
    session: Session,
    action: CorporateAction,
) -> Dict:
    """Áp dụng biến động cổ phiếu: điều chỉnh giao dịch và giá lịch sử.

    Điều chỉnh ALL Transaction và PriceSnapshot records cho asset này
    where date < ex_date. Sets action.applied = True.
    All changes committed in ONE transaction (atomic).

    Trả về dict tóm tắt số lượng bản ghi đã điều chỉnh.
    """
    # Idempotency guard — prevent double-application
    if action.applied:
        raise ValueError("Corporate action already applied")

    # Parse ex_date
    try:
        ex_date_obj = datetime.date.fromisoformat(action.ex_date)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid ex_date: {action.ex_date}")

    # Compute adjustment factors
    qty_factor, price_factor = get_transaction_factors(
        action.action_type, action.ratio or ""
    )

    # If no adjustment needed (rights, cash_dividend), just mark applied
    if qty_factor == Decimal("1") and price_factor == Decimal("1"):
        action.applied = True
        session.add(action)
        session.commit()
        session.refresh(action)
        return {
            "transactions_adjusted": 0,
            "prices_adjusted": 0,
            "applied": True,
        }

    # --- Adjust Transaction records (quantity, price) ---
    txns: List[Transaction] = session.exec(
        select(Transaction).where(
            Transaction.asset_id == action.asset_id,
            Transaction.date < ex_date_obj,
        )
    ).all()

    txn_count = 0
    for txn in txns:
        # quantity *= qty_factor (multiply shares)
        txn.quantity = (txn.quantity * qty_factor).quantize(Decimal("0.0001"))
        # price *= price_factor (divide price — same factor as price adjustment)
        txn.price = (txn.price * price_factor).quantize(Decimal("0.01"))
        session.add(txn)
        txn_count += 1

    # --- Adjust PriceSnapshot records (existing logic, now Decimal) ---
    prices: List[PriceSnapshot] = session.exec(
        select(PriceSnapshot).where(
            PriceSnapshot.asset_id == action.asset_id,
            PriceSnapshot.date < ex_date_obj,
        )
    ).all()

    price_count = 0
    for snap in prices:
        snap.price = (snap.price * price_factor).quantize(Decimal("0.0001"))
        if snap.change is not None:
            snap.change = (snap.change * price_factor).quantize(Decimal("0.0001"))
        session.add(snap)
        price_count += 1

    # --- Mark as applied ---
    action.applied = True
    session.add(action)

    # Commit ALL changes in ONE transaction (atomic)
    session.commit()
    session.refresh(action)

    return {
        "transactions_adjusted": txn_count,
        "prices_adjusted": price_count,
        "applied": True,
    }


# Backward-compatible alias
def apply_corporate_action_to_prices(
    session: Session,
    action: CorporateAction,
) -> int:
    """Deprecated alias for apply_corporate_action. Returns prices_adjusted count."""
    result = apply_corporate_action(session, action)
    return result["prices_adjusted"]


def get_corporate_actions(
    session: Session, asset_id: Optional[int] = None
) -> List[CorporateAction]:
    """Lấy danh sách biến động cổ phiếu, có thể lọc theo asset."""
    stmt = select(CorporateAction).order_by(CorporateAction.ex_date.desc())
    if asset_id is not None:
        stmt = stmt.where(CorporateAction.asset_id == asset_id)
    return session.exec(stmt).all()


def get_adjustment_summary(session: Session, asset_id: int) -> List[Dict]:
    """Tóm tắt các lần điều chỉnh giá cho một asset."""
    actions = get_corporate_actions(session, asset_id)
    summary = []
    for action in actions:
        factor = get_adjustment_factor(action.action_type, action.ratio or "")
        summary.append({
            "id": action.id,
            "action_type": action.action_type,
            "ex_date": action.ex_date,
            "ratio": action.ratio,
            "adjustment_factor": round(factor, 6),
            "applied": action.applied,
            "notes": action.notes,
        })
    return summary
