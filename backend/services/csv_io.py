import csv
import datetime
import io
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import CsvImportResult
from services.asset_type_config import get_asset_type_codes, is_market_price_type
from services.market_data import MarketDataService
from services.transaction_types import (
    is_buy_type,
    is_sell_type,
    MARKET_TRANSACTION_TYPES,
    NON_MARKET_TRANSACTION_TYPES,
)


ASSET_HEADERS = ["symbol", "name", "type", "exchange", "currency", "value"]
TRANSACTION_HEADERS = ["symbol", "type", "quantity", "price", "fee", "date", "notes"]


def parse_number(raw: str) -> Decimal:
    """Parse a number string that may use comma as decimal or thousands separator.

    Rules:
    - If string has both comma and dot: assume dot is decimal, comma is thousands -> remove commas
    - If string has only comma:
      - If comma is followed by exactly 1-2 digits at end -> comma is decimal -> replace with dot
      - Otherwise -> comma is thousands -> remove
    - If string has only dot: dot is decimal -> keep as-is
    """
    s = raw.strip().replace(" ", "")
    if not s:
        return Decimal("0")
    # Remove currency symbols
    for sym in ("₫", "$", "€", "£", "¥", "VND", "USD", "EUR"):
        s = s.replace(sym, "")
    s = s.strip()

    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # Both present: assume comma=thousands, dot=decimal (US format)
        s = s.replace(",", "")
    elif has_comma:
        # Only comma: check if it's decimal (1-2 digits after) or thousands
        parts = s.rsplit(",", 1)
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Comma is decimal separator (Vietnamese format)
            s = parts[0].replace(",", "") + "." + parts[1]
        else:
            # Comma is thousands separator
            s = s.replace(",", "")

    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")


def parse_date(raw: str) -> datetime.date:
    """Parse a date string trying multiple formats."""
    raw = raw.strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {raw}. Use YYYY-MM-DD or DD/MM/YYYY.")


def _sanitize_csv_cell(value: str) -> str:
    """Prefix dangerous formula characters to prevent CSV injection."""
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def export_assets(session: Session) -> str:
    assets = session.exec(select(Asset).where(Asset.is_active == True).order_by(Asset.symbol)).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ASSET_HEADERS, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for a in assets:
        latest_snapshot = session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == a.id)
            .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
        ).first()
        writer.writerow({
            "symbol": _sanitize_csv_cell(a.symbol),
            "name": _sanitize_csv_cell(a.name),
            "type": _sanitize_csv_cell(a.type),
            "exchange": _sanitize_csv_cell(a.exchange or ""),
            "currency": _sanitize_csv_cell(a.currency),
            "value": latest_snapshot.price if latest_snapshot else "",
        })
    return output.getvalue()


def export_transactions(session: Session) -> str:
    transactions = session.exec(
        select(Transaction).order_by(Transaction.date.desc())
    ).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRANSACTION_HEADERS, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for t in transactions:
        asset = session.get(Asset, t.asset_id)
        writer.writerow({
            "symbol": _sanitize_csv_cell(asset.symbol if asset else ""),
            "type": _sanitize_csv_cell(t.type),
            "quantity": t.quantity,
            "price": t.price,
            "fee": t.fee,
            "date": t.date.isoformat(),
            "notes": _sanitize_csv_cell(t.notes or ""),
        })
    return output.getvalue()


def import_assets(session: Session, content: str) -> CsvImportResult:
    reader = csv.DictReader(io.StringIO(content))
    rows = [dict(row) for row in reader]
    return import_assets_from_rows(session, rows)


def _parse_optional_value(row: Dict[str, Any]) -> Optional[Decimal]:
    raw = (row.get("value") or "").strip()
    if not raw:
        return None
    value = parse_number(raw)
    return value if value > 0 else None


def import_assets_from_rows(session: Session, rows: List[Dict[str, Any]]) -> CsvImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []
    try:
        for i, row in enumerate(rows, start=2):
            symbol = (row.get("symbol") or "").strip().upper()
            name = (row.get("name") or "").strip()
            type_ = (row.get("type") or "").strip().upper()
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

            if not is_market_price_type(session, type_):
                value = _parse_optional_value(row)
                if value is None:
                    errors.append(f"Row {i}: asset type {type_} requires a positive value")
                    skipped += 1
                    continue
            else:
                value = _parse_optional_value(row)

            asset = Asset(
                symbol=symbol,
                name=name,
                type=type_,
                exchange=(row.get("exchange") or "").strip() or None,
                currency=(row.get("currency") or "VND").strip(),
            )
            session.add(asset)
            session.flush()
            session.refresh(asset)
            created += 1

            if value:
                today = datetime.date.today()
                existing = session.exec(
                    select(PriceSnapshot).where(
                        PriceSnapshot.asset_id == asset.id,
                        PriceSnapshot.date == today,
                    )
                ).first()
                if existing:
                    existing.price = value
                else:
                    session.add(
                        PriceSnapshot(
                            asset_id=asset.id,
                            date=today,
                            price=value,
                        )
                    )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return CsvImportResult(created=created, skipped=skipped, errors=errors)


def import_transactions(session: Session, content: str) -> CsvImportResult:
    reader = csv.DictReader(io.StringIO(content))
    rows = [dict(row) for row in reader]
    return import_transactions_from_rows(session, rows)


def import_transactions_from_rows(session: Session, rows: List[Dict[str, Any]]) -> CsvImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []
    try:
        for i, row in enumerate(rows, start=2):
            symbol = (row.get("symbol") or "").strip().upper()
            type_ = (row.get("type") or "").strip().upper()
            if not symbol or type_ not in MARKET_TRANSACTION_TYPES | NON_MARKET_TRANSACTION_TYPES:
                errors.append(f"Row {i}: invalid symbol or type")
                skipped += 1
                continue
            try:
                quantity = parse_number(row.get("quantity", "0"))
                price = parse_number(row.get("price", "0"))
                fee = parse_number(row.get("fee", "0"))
                date = parse_date(row.get("date", ""))
            except Exception as e:
                errors.append(f"Row {i}: invalid numeric/date field ({e})")
                skipped += 1
                continue

            if quantity <= 0 or fee < 0:
                errors.append(f"Row {i}: quantity/fee must be positive")
                skipped += 1
                continue

            asset = session.exec(
                select(Asset).where(Asset.symbol == symbol, Asset.is_active == True)
            ).first()
            if not asset:
                # Auto-create a stock asset if not found.
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

            if price <= 0 and is_market_price_type(session, asset.type):
                resolved = MarketDataService(session).resolve_historical_price(asset, date)
                if resolved is not None:
                    price = resolved

            if price <= 0 and not is_market_price_type(session, asset.type):
                snapshot = session.exec(
                    select(PriceSnapshot)
                    .where(PriceSnapshot.asset_id == asset.id)
                    .order_by(PriceSnapshot.date.desc(), PriceSnapshot.id.desc())
                ).first()
                if snapshot and snapshot.price > 0:
                    price = snapshot.price

            if price <= 0:
                errors.append(f"Row {i}: price must be positive or resolvable from market data")
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
                notes=(row.get("notes") or "").strip() or None,
            )
            session.add(tx)
            created += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    return CsvImportResult(created=created, skipped=skipped, errors=errors)
