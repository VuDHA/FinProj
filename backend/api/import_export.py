from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from database import get_session
from schemas import CsvImportResult
from services import csv_io

router = APIRouter(prefix="/import-export", tags=["import-export"])


@router.get("/export/assets")
def export_assets(session: Session = Depends(get_session)):
    data = csv_io.export_assets(session)
    return PlainTextResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assets.csv"},
    )


@router.get("/export/transactions")
def export_transactions(session: Session = Depends(get_session)):
    data = csv_io.export_transactions(session)
    return PlainTextResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.post("/import/assets", response_model=CsvImportResult)
def import_assets(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = file.file.read().decode("utf-8")
    return csv_io.import_assets(session, content)


@router.post("/import/transactions", response_model=CsvImportResult)
def import_transactions(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = file.file.read().decode("utf-8")
    return csv_io.import_transactions(session, content)
