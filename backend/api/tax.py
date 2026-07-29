"""API routes for tax DISPLAY module (Thuế - chỉ hiển thị ước tính).

IMPORTANT: Module này chỉ HIỂN THỊ thông tin thuế tham khảo, không tự động
tính toán hay thay đổi giao dịch. Tất cả bản ghi đều được đánh dấu is_estimated=True.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import get_session
from schemas import TaxRecordRead, TaxYearSummary
from services.tax import (
    TAX_DISCLAIMER,
    get_tax_records_for_year,
    get_tax_year_summary,
    generate_tax_estimates,
)

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/{year}", response_model=List[TaxRecordRead])
def get_tax_records(year: int, session: Session = Depends(get_session)):
    """Hiển thị bản ghi thuế ước tính cho một năm.

    Tất cả bản ghi đều là ước tính (is_estimated=True), chỉ mang tính tham khảo.
    """
    return get_tax_records_for_year(session, year)


@router.get("/{year}/summary", response_model=TaxYearSummary)
def get_tax_summary(year: int, session: Session = Depends(get_session)):
    """Tổng quan thuế năm: tổng thuế lãi vốn, thuế cổ tức, phí chuyển nhượng.

    Kèm disclaimer: các con số chỉ là ước tính tham khảo.
    """
    return get_tax_year_summary(session, year)


@router.post("/{year}/generate")
def generate_tax(year: int, session: Session = Depends(get_session)):
    """Tạo bản ghi thuế ước tính dựa trên giao dịch hiện có.

    KHÔNG thay đổi giao dịch, chỉ tạo các bản ghi TaxRecord để hiển thị.
    Tất cả bản ghi đều có is_estimated=True.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid tax year")

    result = generate_tax_estimates(session, year)
    return result
