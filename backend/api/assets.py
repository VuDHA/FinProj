import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Asset, PriceSnapshot
from schemas import AssetCreate, AssetRead
from services.asset_type_config import (
    generate_symbol,
    get_asset_types,
    is_market_price_type,
    is_valid_asset_type,
)
from services.source_config import is_valid_source_for_type

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/", response_model=List[AssetRead])
def list_assets(session: Session = Depends(get_session)):
    return session.exec(select(Asset).where(Asset.is_active == True)).all()


@router.post("/", response_model=AssetRead)
def create_asset(asset: AssetCreate, session: Session = Depends(get_session)):
    if not is_valid_asset_type(session, asset.type):
        valid_types = ", ".join(sorted(get_asset_types(session).keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported asset type: {asset.type}. Must be one of {valid_types}",
        )

    if asset.source and not is_valid_source_for_type(asset.source, asset.type):
        raise HTTPException(
            status_code=400,
            detail=f"Source {asset.source} is not supported for asset type {asset.type}",
        )

    if not is_market_price_type(session, asset.type):
        if asset.manual_value is None or asset.manual_value <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Asset type {asset.type} requires a positive manual value",
            )

    payload = asset.model_dump()
    if payload.get("source") == "":
        payload["source"] = None

    if not payload.get("symbol"):
        payload["symbol"] = generate_symbol(payload["name"], payload["type"])

    existing = session.exec(
        select(Asset).where(Asset.symbol == payload["symbol"], Asset.is_active == True)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Asset symbol already exists")

    manual_value = payload.pop("manual_value", None)
    db_asset = Asset(**payload)
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)

    if manual_value:
        session.add(
            PriceSnapshot(
                asset_id=db_asset.id,
                date=datetime.date.today(),
                price=float(manual_value),
            )
        )
        session.commit()

    return db_asset


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, session: Session = Depends(get_session)):
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.is_active = False
    session.add(asset)
    session.commit()
    return {"ok": True}
