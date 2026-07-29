import datetime
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlmodel import Session

from config import settings
from models import Asset, PriceSnapshot, Transaction
from schemas import CsvImportResult
from services.asset_type_config import get_asset_type_codes, is_market_price_type
from services.csv_io import parse_date, parse_number
from services.file_utils import read_excel_sheet_names, read_rows
from services.transaction_types import (
    is_buy_type,
    is_sell_type,
    MARKET_TRANSACTION_TYPES,
    NON_MARKET_TRANSACTION_TYPES,
)


ASSET_TARGET_FIELDS = ["symbol", "name", "type", "exchange", "currency", "value"]
REQUIRED_ASSET_FIELDS = ["symbol", "name", "type"]
TRANSACTION_TARGET_FIELDS = ["symbol", "type", "quantity", "price", "fee", "date", "notes"]
REQUIRED_TRANSACTION_FIELDS = ["symbol", "type", "quantity", "price", "date"]


class SmartImportService:
    """Preview and import CSV/Excel files with AI-assisted header mapping.

    Uses Gemini batch when AI_PROVIDER=gemini; otherwise falls back to Ollama
    or keyword-based matching.
    """

    def __init__(self, model: str = settings.OLLAMA_MODEL):
        self.model = model

    @staticmethod
    def _is_csv(filename: str) -> bool:
        return filename.lower().endswith(".csv")

    @staticmethod
    def _is_excel(filename: str) -> bool:
        return filename.lower().endswith(".xlsx")

    @staticmethod
    def _is_zip(filename: str) -> bool:
        return filename.lower().endswith(".zip")

    def _read_rows(
        self, content: bytes, filename: str, sheet_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            return read_rows(content, filename, sheet_name=sheet_name)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Cannot read file: {e}") from e

    def preview(
        self, content: bytes, filename: str, sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return sheet names, headers, and sample rows for a file."""
        rows = self._read_rows(content, filename, sheet_name=sheet_name)
        headers = list(rows[0].keys()) if rows else []
        sample = rows[:5]

        sheet_names = None
        actual_sheet = sheet_name
        if self._is_excel(filename):
            try:
                sheet_names = read_excel_sheet_names(content)
            except ValueError:
                sheet_names = None
            if actual_sheet is None and sheet_names:
                actual_sheet = sheet_names[0]

        return {
            "filename": filename,
            "sheet_names": sheet_names,
            "sheet": actual_sheet,
            "headers": headers,
            "sample_rows": sample,
            "row_count": len(rows),
        }

    def _build_mapping_prompt(
        self, headers: List[str], import_type: str, language: str = "vi"
    ) -> str:
        target_fields = (
            ASSET_TARGET_FIELDS if import_type == "assets" else TRANSACTION_TARGET_FIELDS
        )
        if language == "vi":
            return (
                "Bạn là trợ lý tài chính. Bạn nhận được danh sách tiêu đề cột từ file CSV/Excel. "
                "Hãy ánh xạ mỗi tiêu đề sang một trường đích phù hợp. "
                "Trả về một JSON object duy nhất với key là tiêu đề gốc và value là trường đích. "
                "Nếu không khớp, dùng null. Không thêm giải thích.\n\n"
                f"Loại import: {import_type}\n"
                f"Trường đích: {', '.join(target_fields)}\n"
                f"Tiêu đề: {', '.join(headers)}\n\n"
                "JSON:"
            )
        return (
            "You are a financial assistant. Map each source column header to a target field. "
            "Return a single JSON object where keys are the original headers and values are target fields. "
            "Use null if no match. No commentary.\n\n"
            f"Import type: {import_type}\n"
            f"Target fields: {', '.join(target_fields)}\n"
            f"Headers: {', '.join(headers)}\n\n"
            "JSON:"
        )

    def suggest_mapping(
        self, headers: List[str], import_type: str, language: str = "vi"
    ) -> Dict[str, Optional[str]]:
        """Use the AI provider to suggest a header-to-target mapping."""
        if not self._is_ai_enabled():
            return {h: self._fallback_mapping(h, import_type) for h in headers}

        try:
            from services.batch_ai import BatchAIService

            service = BatchAIService(batch_size=1)
            return service.suggest_mappings([headers], import_type, language=language)[0]
        except Exception as e:
            print(f"[smart_import] mapping failed: {e}")
            return {h: self._fallback_mapping(h, import_type) for h in headers}

    def _is_ai_enabled(self) -> bool:
        return settings.AI_PROVIDER == "gemini" or settings.OLLAMA_ENABLED

    @staticmethod
    def _fallback_mapping(header: str, import_type: str) -> Optional[str]:
        """Simple keyword-based fallback mapping."""
        h = header.lower().strip()
        target_fields = (
            ASSET_TARGET_FIELDS if import_type == "assets" else TRANSACTION_TARGET_FIELDS
        )
        for field in target_fields:
            if field in h or h in field:
                return field
            # Vietnamese common aliases
            aliases = {
                "symbol": ["mã", "ticker", "mã cp"],
                "name": ["tên", "tên tài sản", "tên cp"],
                "type": ["loại", "loại tài sản"],
                "exchange": ["sàn"],
                "currency": ["tiền tệ", "đơn vị tiền"],
                "value": ["giá trị", "giá", "định giá", "giá trị tài sản"],
                "quantity": ["số lượng", "khối lượng"],
                "price": ["giá", "đơn giá"],
                "fee": ["phí", "hoa hồng"],
                "date": ["ngày"],
                "notes": ["ghi chú", "mô tả"],
            }
            if field in aliases and any(alias in h for alias in aliases[field]):
                return field
        return None

    def import_data(
        self,
        session: Session,
        content: bytes,
        filename: str,
        import_type: str,
        mapping: Dict[str, Optional[str]],
        sheet_name: Optional[str] = None,
    ) -> CsvImportResult:
        """Import a file using the provided header-to-target mapping."""
        rows = self._read_rows(content, filename, sheet_name=sheet_name)
        if not rows:
            return CsvImportResult(created=0, skipped=0, errors=["No rows found in file"])

        target_fields = (
            ASSET_TARGET_FIELDS if import_type == "assets" else TRANSACTION_TARGET_FIELDS
        )
        required_fields = (
            REQUIRED_ASSET_FIELDS if import_type == "assets" else REQUIRED_TRANSACTION_FIELDS
        )
        # Invert mapping: target -> source header
        target_to_source = {v: k for k, v in mapping.items() if v in target_fields}
        missing = [f for f in required_fields if f not in target_to_source]
        if missing:
            return CsvImportResult(
                created=0,
                skipped=0,
                errors=[f"Missing required mappings: {', '.join(missing)}"],
            )

        if import_type == "assets":
            return self._import_assets(session, rows, target_to_source)
        if import_type == "transactions":
            return self._import_transactions(session, rows, target_to_source)
        return CsvImportResult(created=0, skipped=0, errors=["Invalid import type"])

    @staticmethod
    def _parse_value(row: Dict[str, Any], target_to_source: Dict[str, str]) -> Optional[Decimal]:
        raw = (row.get(target_to_source.get("value", "")) or "").strip()
        if not raw:
            return None
        value = parse_number(raw)
        return value if value > 0 else None

    def _import_assets(
        self, session: Session, rows: List[Dict[str, Any]], target_to_source: Dict[str, str]
    ) -> CsvImportResult:
        created = 0
        skipped = 0
        errors: List[str] = []
        try:
            for i, row in enumerate(rows, start=2):
                symbol = (row.get(target_to_source.get("symbol", "")) or "").strip().upper()
                name = (row.get(target_to_source.get("name", "")) or "").strip()
                type_ = (row.get(target_to_source.get("type", "")) or "").strip().upper()
                if not symbol or not name or not type_:
                    errors.append(f"Row {i}: missing symbol/name/type")
                    skipped += 1
                    continue
                if type_ not in get_asset_type_codes(session):
                    errors.append(f"Row {i}: invalid asset type {type_}")
                    skipped += 1
                    continue
                existing = session.exec(
                    select(Asset).where(Asset.symbol == symbol, Asset.is_active == True)
                ).first()
                if existing:
                    skipped += 1
                    continue

                value = self._parse_value(row, target_to_source)
                if not is_market_price_type(session, type_):
                    if value is None:
                        errors.append(f"Row {i}: asset type {type_} requires a positive value")
                        skipped += 1
                        continue

                asset = Asset(
                    symbol=symbol,
                    name=name,
                    type=type_,
                    exchange=(row.get(target_to_source.get("exchange", "")) or "").strip() or None,
                    currency=(row.get(target_to_source.get("currency", "")) or "VND").strip() or "VND",
                )
                session.add(asset)
                session.flush()
                session.refresh(asset)
                created += 1

                if value:
                    session.add(
                        PriceSnapshot(
                            asset_id=asset.id,
                            date=datetime.date.today(),
                            price=value,
                        )
                    )
            session.commit()
        except Exception:
            session.rollback()
            raise
        return CsvImportResult(created=created, skipped=skipped, errors=errors)

    def _import_transactions(
        self, session: Session, rows: List[Dict[str, Any]], target_to_source: Dict[str, str]
    ) -> CsvImportResult:
        created = 0
        skipped = 0
        errors: List[str] = []

        try:
            for i, row in enumerate(rows, start=2):
                symbol = (row.get(target_to_source.get("symbol", "")) or "").strip().upper()
                type_ = (row.get(target_to_source.get("type", "")) or "").strip().upper()
                if not symbol or type_ not in MARKET_TRANSACTION_TYPES | NON_MARKET_TRANSACTION_TYPES:
                    errors.append(f"Row {i}: invalid symbol or type")
                    skipped += 1
                    continue
                try:
                    quantity = parse_number(
                        row.get(target_to_source.get("quantity", "")) or "0"
                    )
                    price = parse_number(
                        row.get(target_to_source.get("price", "")) or "0"
                    )
                    fee = parse_number(
                        row.get(target_to_source.get("fee", "")) or "0"
                    )
                    date = parse_date(
                        (row.get(target_to_source.get("date", "")) or "").strip()
                    )
                except Exception as e:
                    errors.append(f"Row {i}: invalid numeric/date field ({e})")
                    skipped += 1
                    continue

                if quantity <= 0 or price < 0 or fee < 0:
                    errors.append(f"Row {i}: quantity/price/fee must be positive")
                    skipped += 1
                    continue

                asset = session.exec(
                    select(Asset).where(Asset.symbol == symbol, Asset.is_active == True)
                ).first()
                if not asset:
                    asset = Asset(symbol=symbol, name=symbol, type="STOCK")
                    session.add(asset)
                    session.flush()
                    session.refresh(asset)

                allowed_types = (
                    NON_MARKET_TRANSACTION_TYPES
                    if not is_market_price_type(session, asset.type)
                    else MARKET_TRANSACTION_TYPES
                )
                if type_ not in allowed_types:
                    errors.append(
                        f"Row {i}: type {type_} is not allowed for {asset.type} assets"
                    )
                    skipped += 1
                    continue

                if price <= 0 and not is_market_price_type(session, asset.type):
                    snapshot = session.exec(
                        select(PriceSnapshot)
                        .where(PriceSnapshot.asset_id == asset.id)
                        .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
                    ).first()
                    if snapshot and snapshot.price > 0:
                        price = snapshot.price

                if price <= 0:
                    errors.append(f"Row {i}: price must be positive or resolvable")
                    skipped += 1
                    continue

                if is_sell_type(type_):
                    existing = session.exec(
                        select(Transaction).where(Transaction.asset_id == asset.id)
                    ).all()
                    holding = sum(
                        (t.quantity if is_buy_type(t.type) else -t.quantity) for t in existing
                    )
                    if quantity > holding:
                        errors.append(f"Row {i}: cannot sell {quantity}, holding is {holding}")
                        skipped += 1
                        continue

                # Duplicate transaction detection (C5)
                existing_tx = session.exec(
                    select(Transaction).where(
                        Transaction.asset_id == asset.id,
                        Transaction.type == type_,
                        Transaction.quantity == quantity,
                        Transaction.price == price,
                        Transaction.date == date,
                    )
                ).first()
                if existing_tx:
                    errors.append(f"Row {i}: duplicate transaction already exists")
                    skipped += 1
                    continue

                tx = Transaction(
                    asset_id=asset.id,
                    type=type_,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    date=date,
                    notes=(row.get(target_to_source.get("notes", "")) or "").strip() or None,
                )
                session.add(tx)
                created += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        return CsvImportResult(created=created, skipped=skipped, errors=errors)
