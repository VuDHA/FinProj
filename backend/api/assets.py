from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Asset
from schemas import AssetCreate, AssetRead

router = APIRouter(prefix="/assets", tags=["assets"])

VALID_ASSET_TYPES = {"STOCK", "FUND", "ETF", "GOLD", "CRYPTO"}


@router.get("/", response_model=List[AssetRead])
def list_assets(session: Session = Depends(get_session)):
    return session.exec(select(Asset).where(Asset.is_active == True)).all()


@router.post("/", response_model=AssetRead)
def create_asset(asset: AssetCreate, session: Session = Depends(get_session)):
    if asset.type not in VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported asset type: {asset.type}. Must be one of {', '.join(sorted(VALID_ASSET_TYPES))}",
        )

    existing = session.exec(
        select(Asset).where(Asset.symbol == asset.symbol, Asset.is_active == True)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Asset symbol already exists")
    db_asset = Asset(**asset.model_dump())
    session.add(db_asset)
    session.commit()
    session.refresh(db_asset)
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
