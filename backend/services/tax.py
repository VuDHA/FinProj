"""Business logic for tax DISPLAY module (Thuế - chỉ hiển thị ước tính).

IMPORTANT: Đây là module hiển thị (DISPLAY ONLY), không tự động tính toán
hoặc thay đổi giao dịch. Các bản ghi thuế được tạo ra chỉ để tham khảo,
được đánh dấu is_estimated=True.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, TaxRecord, Transaction
from schemas import TaxSummary, TaxYearSummary

# Vietnamese tax rates (Thuế suất Việt Nam)
TRANSFER_TAX_RATE = Decimal("0.001")  # 0.1% thuế chuyển nhượng
DIVIDEND_TAX_RATE = Decimal("0.05")  # 5% thuế cổ tức
CAPITAL_GAINS_TAX_RATE = Decimal("0")  # Miễn thuế TNCN đối với chuyển nhượng chứng khoán (theo TT 111/2013)

# Disclaimer (Thông báo miễn trừ trách nhiệm)
TAX_DISCLAIMER = "Các con số này chỉ là ước tính tham khảo, không thay thế cho tư vấn thuế chuyên nghiệp"


def get_tax_records_for_year(session: Session, tax_year: int) -> List[Dict]:
    """Lấy danh sách bản ghi thuế cho một năm (chỉ ước tính)."""
    stmt = (
        select(TaxRecord, Asset)
        .join(Asset, TaxRecord.asset_id == Asset.id, isouter=True)
        .where(TaxRecord.tax_year == tax_year)
        .order_by(TaxRecord.created_at.desc())
    )
    results = session.exec(stmt).all()

    items = []
    for record, asset in results:
        item = {
            "id": record.id,
            "tax_year": record.tax_year,
            "transaction_id": record.transaction_id,
            "asset_id": record.asset_id,
            "tax_type": record.tax_type,
            "taxable_amount": record.taxable_amount,
            "tax_rate": record.tax_rate,
            "tax_amount": record.tax_amount,
            "is_estimated": record.is_estimated,
            "notes": record.notes,
            "created_at": record.created_at,
            "symbol": asset.symbol if asset else None,
        }
        items.append(item)
    return items


def calculate_yearly_summary(session: Session, tax_year: int) -> TaxSummary:
    """Tính tổng quan thuế cho một năm."""
    records: List[TaxRecord] = session.exec(
        select(TaxRecord).where(TaxRecord.tax_year == tax_year)
    ).all()

    total_capital_gains = Decimal("0")
    total_dividend = Decimal("0")
    total_transfer = Decimal("0")

    for r in records:
        if r.tax_type == "capital_gains":
            total_capital_gains += r.tax_amount
        elif r.tax_type == "dividend":
            total_dividend += r.tax_amount
        elif r.tax_type == "transfer_fee":
            total_transfer += r.tax_amount

    total_tax = (total_capital_gains + total_dividend + total_transfer).quantize(Decimal("0.01"))

    return TaxSummary(
        total_capital_gains_tax=total_capital_gains.quantize(Decimal("0.01")),
        total_dividend_tax=total_dividend.quantize(Decimal("0.01")),
        total_transfer_fee=total_transfer.quantize(Decimal("0.01")),
        total_tax=total_tax,
        record_count=len(records),
    )


def get_tax_year_summary(session: Session, tax_year: int) -> TaxYearSummary:
    """Trả về tổng quan thuế năm kèm disclaimer."""
    summary = calculate_yearly_summary(session, tax_year)
    return TaxYearSummary(
        tax_year=tax_year,
        summary=summary,
        disclaimer=TAX_DISCLAIMER,
    )


def generate_tax_estimates(session: Session, tax_year: int) -> Dict:
    """Tạo bản ghi thuế ước tính dựa trên giao dịch hiện có.

    CHÚ Ý: Hàm này KHÔNG thay đổi giao dịch, chỉ tạo các bản ghi TaxRecord
    để hiển thị ước tính thuế. Tất cả bản ghi đều có is_estimated=True.

    Logic:
    - transfer_fee: 0.1% trên giá trị giao dịch (BUY + SELL)
    - dividend: 5% trên cổ tức (từ Income type=DIVIDEND)
    - capital_gains: ước tính lãi vốn từ giao dịch SELL (nếu có)
    """
    # Xóa các bản ghi ước tính cũ cho năm này (để tránh trùng lặp khi regenerate)
    old_records = session.exec(
        select(TaxRecord).where(TaxRecord.tax_year == tax_year, TaxRecord.is_estimated == True)
    ).all()
    for old in old_records:
        session.delete(old)
    session.commit()

    created_count = 0

    # 1. Transfer fee (thuế chuyển nhượng 0.1%) trên tất cả giao dịch BUY/SELL
    txns: List[Transaction] = session.exec(
        select(Transaction).where(
            Transaction.type.in_(["BUY", "SELL"]),
        )
    ).all()

    for txn in txns:
        # Lọc theo năm (dựa trên date)
        if txn.date.year != tax_year:
            continue
        taxable_amount = (txn.quantity * txn.price).quantize(Decimal("0.01"))
        tax_amount = (taxable_amount * TRANSFER_TAX_RATE).quantize(Decimal("0.0001"))
        if tax_amount <= 0:
            continue
        record = TaxRecord(
            tax_year=tax_year,
            transaction_id=txn.id,
            asset_id=txn.asset_id,
            tax_type="transfer_fee",
            taxable_amount=taxable_amount,
            tax_rate=TRANSFER_TAX_RATE,
            tax_amount=tax_amount,
            is_estimated=True,
            notes=f"Thuế chuyển nhượng 0.1% cho giao dịch {txn.type} #{txn.id}",
        )
        session.add(record)
        created_count += 1

    # 2. Dividend tax (5%) từ Income records type=DIVIDEND
    from models import Income
    incomes = session.exec(
        select(Income).where(Income.type == "DIVIDEND")
    ).all()

    for inc in incomes:
        if inc.date.year != tax_year:
            continue
        tax_amount = (inc.amount * DIVIDEND_TAX_RATE).quantize(Decimal("0.01"))
        if tax_amount <= 0:
            continue
        record = TaxRecord(
            tax_year=tax_year,
            asset_id=inc.asset_id,
            tax_type="dividend",
            taxable_amount=inc.amount,
            tax_rate=DIVIDEND_TAX_RATE,
            tax_amount=tax_amount,
            is_estimated=True,
            notes=f"Thuế cổ tức 5% cho khoản thu nhập #{inc.id}",
        )
        session.add(record)
        created_count += 1

    # 3. Capital gains (lãi vốn) - ước tính từ giao dịch SELL
    # Tính lãi/lỗ cho mỗi giao dịch SELL dựa trên giá vốn trung bình
    # Theo luật VN hiện hành, chuyển nhượng CK cá nhân được miễn thuế TNCN
    # nhưng vẫn hiển thị ước tính để tham khảo
    sell_txns = [t for t in txns if t.type == "SELL" and t.date.year == tax_year]
    for sell in sell_txns:
        # Tính giá vốn trung bình của các lô BUY trước ngày SELL
        buy_txns = session.exec(
            select(Transaction).where(
                Transaction.asset_id == sell.asset_id,
                Transaction.type == "BUY",
                Transaction.date <= sell.date,
            )
        ).all()

        total_buy_qty = sum((b.quantity for b in buy_txns), Decimal("0"))
        total_buy_cost = sum(((b.quantity * b.price + b.fee) for b in buy_txns), Decimal("0"))

        if total_buy_qty > 0:
            avg_cost = total_buy_cost / total_buy_qty
            proceeds = sell.quantity * sell.price - sell.fee
            cost_basis = sell.quantity * avg_cost
            capital_gain = proceeds - cost_basis

            if capital_gain > 0:
                tax_amount = (capital_gain * CAPITAL_GAINS_TAX_RATE).quantize(Decimal("0.01"))
                record = TaxRecord(
                    tax_year=tax_year,
                    transaction_id=sell.id,
                    asset_id=sell.asset_id,
                    tax_type="capital_gains",
                    taxable_amount=capital_gain.quantize(Decimal("0.01")),
                    tax_rate=CAPITAL_GAINS_TAX_RATE,
                    tax_amount=tax_amount,
                    is_estimated=True,
                    notes=f"Thuế lãi vốn ước tính cho giao dịch SELL #{sell.id} (miễn thuế theo TT 111/2013)",
                )
                session.add(record)
                created_count += 1

    session.commit()

    return {
        "tax_year": tax_year,
        "records_created": created_count,
        "is_estimated": True,
        "disclaimer": TAX_DISCLAIMER,
    }
