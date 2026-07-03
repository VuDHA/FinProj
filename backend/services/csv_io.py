import csv
import datetime
import io
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Transaction
from schemas import CsvImportResult
from services.asset_type_config import get_asset_type_codes, is_market_price_type
from services.market_data import MarketDataService


ASSET_HEADERS = ["symbol", "name", "type", "exchange", "currency", "value"]
TRANSACTION_HEADERS = ["symbol", "type", "quantity", "price", "fee", "date", "notes"]


def export_assets(session: Session) -> str:
    assets = session.exec(select(Asset).where(Asset.is_active == True).order_by(Asset.symbol)).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ASSET_HEADERS)
    writer.writeheader()
    for a in assets:
        latest_snapshot = session.exec(
            select(PriceSnapshot)
            .where(PriceSnapshot.asset_id == a.id)
            .order_by(PriceSnapshot.date.desc())
        ).first()
        writer.writerow({
            "symbol": a.symbol,
            "name": a.name,
            "type": a.type,
            "exchange": a.exchange or "",
            "currency": a.currency,
            "value": latest_snapshot.price if latest_snapshot else "",
        })
    return output.getvalue()


def export_transactions(session: Session) -> str:
    transactions = session.exec(
        select(Transaction).order_by(Transaction.date.desc())
    ).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TRANSACTION_HEADERS)
    writer.writeheader()
    for t in transactions:
        asset = session.get(Asset, t.asset_id)
        writer.writerow({
            "symbol": asset.symbol if asset else "",
            "type": t.type,
            "quantity": t.quantity,
            "price": t.price,
            "fee": t.fee,
            "date": t.date.isoformat(),
            "notes": t.notes or "",
        })
    return output.getvalue()


def import_assets(session: Session, content: str) -> CsvImportResult:
    reader = csv.DictReader(io.StringIO(content))
    rows = [dict(row) for row in reader]
    return import_assets_from_rows(session, rows)


def _parse_optional_value(row: Dict[str, Any]) -> Optional[float]:
    raw = (row.get("value") or "").strip().replace(",", "")
    if not raw:
        return None
    try:
        value = float(raw)
        return value if value > 0 else None
    except ValueError:
        return None


def import_assets_from_rows(session: Session, rows: List[Dict[str, Any]]) -> CsvImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []
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
        session.commit()
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
    return CsvImportResult(created=created, skipped=skipped, errors=errors)


def import_transactions(session: Session, content: str) -> CsvImportResult:
    reader = csv.DictReader(io.StringIO(content))
    rows = [dict(row) for row in reader]
    return import_transactions_from_rows(session, rows)


def import_transactions_from_rows(session: Session, rows: List[Dict[str, Any]]) -> CsvImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []
    for i, row in enumerate(rows, start=2):
        symbol = (row.get("symbol") or "").strip().upper()
        type_ = (row.get("type") or "").strip().upper()
        if not symbol or type_ not in ("BUY", "SELL"):
            errors.append(f"Row {i}: invalid symbol or type")
            skipped += 1
            continue
        try:
            quantity = float(row.get("quantity", "0").replace(",", ""))
            price = float(row.get("price", "0").replace(",", ""))
            fee = float(row.get("fee", "0").replace(",", ""))
            date = datetime.date.fromisoformat(row.get("date", "").strip())
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
            session.commit()
            session.refresh(asset)

        if price <= 0 and is_market_price_type(session, asset.type):
            resolved = MarketDataService(session).resolve_historical_price(asset, date)
            if resolved is not None:
                price = resolved

        if price <= 0 and not is_market_price_type(session, asset.type):
            snapshot = session.exec(
                select(PriceSnapshot)
                .where(PriceSnapshot.asset_id == asset.id)
                .order_by(PriceSnapshot.date.desc())
            ).first()
            if snapshot and snapshot.price > 0:
                price = snapshot.price

        if price <= 0:
            errors.append(f"Row {i}: price must be positive or resolvable from market data")
            skipped += 1
            continue

        if type_ == "SELL":
            existing = session.exec(
                select(Transaction).where(Transaction.asset_id == asset.id)
            ).all()
            holding = sum(
                t.quantity if t.type == "BUY" else -t.quantity for t in existing
            )
            if quantity > holding:
                errors.append(f"Row {i}: cannot sell {quantity}, holding is {holding}")
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
    return CsvImportResult(created=created, skipped=skipped, errors=errors)
