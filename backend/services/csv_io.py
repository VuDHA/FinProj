import csv
import datetime
import io
from typing import List

from sqlmodel import Session, select

from models import Asset, Transaction
from schemas import CsvImportResult


ASSET_HEADERS = ["symbol", "name", "type", "exchange", "currency"]
TRANSACTION_HEADERS = ["symbol", "type", "quantity", "price", "fee", "date", "notes"]
VALID_ASSET_TYPES = {"STOCK", "FUND", "ETF", "GOLD", "CRYPTO"}


def export_assets(session: Session) -> str:
    assets = session.exec(select(Asset).where(Asset.is_active == True).order_by(Asset.symbol)).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ASSET_HEADERS)
    writer.writeheader()
    for a in assets:
        writer.writerow({
            "symbol": a.symbol,
            "name": a.name,
            "type": a.type,
            "exchange": a.exchange or "",
            "currency": a.currency,
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
    created = 0
    skipped = 0
    errors: List[str] = []
    reader = csv.DictReader(io.StringIO(content))
    for i, row in enumerate(reader, start=2):
        symbol = (row.get("symbol") or "").strip().upper()
        name = (row.get("name") or "").strip()
        type_ = (row.get("type") or "").strip().upper()
        if not symbol or not name or not type_:
            errors.append(f"Row {i}: missing symbol/name/type")
            skipped += 1
            continue
        if type_ not in VALID_ASSET_TYPES:
            errors.append(f"Row {i}: invalid asset type {type_}")
            skipped += 1
            continue
        existing = session.exec(
            select(Asset).where(Asset.symbol == symbol, Asset.is_active == True)
        ).first()
        if existing:
            skipped += 1
            continue
        asset = Asset(
            symbol=symbol,
            name=name,
            type=type_,
            exchange=(row.get("exchange") or "").strip() or None,
            currency=(row.get("currency") or "VND").strip(),
        )
        session.add(asset)
        created += 1
    session.commit()
    return CsvImportResult(created=created, skipped=skipped, errors=errors)


def import_transactions(session: Session, content: str) -> CsvImportResult:
    created = 0
    skipped = 0
    errors: List[str] = []
    reader = csv.DictReader(io.StringIO(content))
    for i, row in enumerate(reader, start=2):
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

        if quantity <= 0 or price < 0 or fee < 0:
            errors.append(f"Row {i}: quantity/price/fee must be positive")
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
