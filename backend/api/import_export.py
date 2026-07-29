import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from database import get_session
from schemas import (
    CsvImportResult,
    SmartImportPreviewResponse,
    SmartImportRequest,
)
from services import csv_io, file_utils
from services.smart_import import SmartImportService

router = APIRouter(prefix="/import-export", tags=["import-export"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def _read_upload_content(file: UploadFile) -> bytes:
    """Read uploaded file content with a max size check (H18)."""
    content = file.file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    return content


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


def _read_simple_import_file(file: UploadFile) -> List[Dict[str, Any]]:
    try:
        file_utils.validate_extension(file.filename, allow_zip=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    content = _read_upload_content(file)
    try:
        return file_utils.read_rows(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/import/assets", response_model=CsvImportResult)
def import_assets(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    rows = _read_simple_import_file(file)
    return csv_io.import_assets_from_rows(session, rows)


@router.post("/import/transactions", response_model=CsvImportResult)
def import_transactions(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    rows = _read_simple_import_file(file)
    return csv_io.import_transactions_from_rows(session, rows)


@router.post("/smart-preview", response_model=SmartImportPreviewResponse)
def smart_import_preview(
    file: UploadFile = File(...),
    sheet: Optional[str] = Form(None),
    import_type: str = Form("assets"),
    session: Session = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        file_utils.validate_extension(file.filename, allow_zip=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    content = _read_upload_content(file)
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
        file_utils.validate_extension(file.filename, allow_zip=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        payload = SmartImportRequest.model_validate_json(payload_json)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {e}")
    content = _read_upload_content(file)
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
