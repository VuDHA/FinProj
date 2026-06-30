import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from database import get_session
from schemas import (
    CsvImportResult,
    SmartImportPreviewResponse,
    SmartImportRequest,
)
from services import csv_io
from services.smart_import import SmartImportService

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


@router.post("/smart-preview", response_model=SmartImportPreviewResponse)
def smart_import_preview(
    file: UploadFile = File(...),
    sheet: Optional[str] = Form(None),
    import_type: str = Form("assets"),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    content = file.file.read()
    service = SmartImportService()
    try:
        preview = service.preview(content, file.filename, sheet_name=sheet)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    preview["suggested_mapping"] = service.suggest_mapping(
        preview["headers"], import_type, language="vi"
    )
    return SmartImportPreviewResponse(**preview)


@router.post("/smart-import", response_model=CsvImportResult)
def smart_import(
    file: UploadFile = File(...),
    payload_json: str = Form(..., alias="payload"),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        payload = SmartImportRequest.model_validate_json(payload_json)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {e}")
    content = file.file.read()
    service = SmartImportService()
    try:
        return service.import_data(
            session,
            content,
            file.filename,
            payload.import_type,
            payload.mapping,
            sheet_name=payload.sheet,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
