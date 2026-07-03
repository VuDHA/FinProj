from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from common.database import get_session
from common.models import AllocationTarget, Setting
from common.schemas import (
    AllocationTargetCreate,
    AllocationTargetRead,
    AssetSourceInfo,
    AssetTypeConfig,
    AssetTypeConfigMap,
    SettingCreate,
    SettingRead,
)
from common.asset_type_config import get_asset_types, save_asset_types
from common.env_config import get_env_config, update_env_config
from services.market.source_config import get_default_sources, is_valid_source_for_type, set_default_sources
from services.market.sources import registry

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=List[SettingRead])
def list_settings(session: Session = Depends(get_session)):
    return session.exec(select(Setting)).all()


@router.get("/sources/{asset_type}", response_model=List[AssetSourceInfo])
def list_sources(asset_type: str):
    return [
        AssetSourceInfo(
            code=source.code,
            name=source.name,
            description=source.description,
            supports_history=source.supports_history,
            supports_listing=source.supports_listing,
        )
        for source in registry.for_type(asset_type.upper())
    ]


@router.get("/default-sources")
def get_default_source_settings(session: Session = Depends(get_session)):
    return get_default_sources(session)


@router.post("/default-sources")
def save_default_source_settings(
    payload: dict,
    session: Session = Depends(get_session),
):
    sources = {}
    for asset_type, source in payload.items():
        asset_type = str(asset_type).upper()
        if not isinstance(source, str) or not is_valid_source_for_type(source, asset_type):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source {source} for asset type {asset_type}",
            )
        sources[asset_type] = source
    return set_default_sources(session, sources)


@router.get("/asset-types", response_model=AssetTypeConfigMap)
def get_asset_type_settings(session: Session = Depends(get_session)):
    return {"types": get_asset_types(session)}


@router.post("/asset-types", response_model=AssetTypeConfigMap)
def save_asset_type_settings(
    payload: AssetTypeConfigMap,
    session: Session = Depends(get_session),
):
    return {"types": save_asset_types(session, {k: v.model_dump() for k, v in payload.types.items()})}


@router.post("/", response_model=SettingRead)
def create_or_update_setting(setting: SettingCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Setting).where(Setting.key == setting.key)).first()
    if existing:
        existing.value = setting.value
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    db_setting = Setting(**setting.model_dump())
    session.add(db_setting)
    session.commit()
    session.refresh(db_setting)
    return db_setting


@router.get("/allocation-targets/", response_model=List[AllocationTargetRead])
def list_allocation_targets(session: Session = Depends(get_session)):
    return session.exec(select(AllocationTarget).order_by(AllocationTarget.type)).all()


@router.post("/allocation-targets/", response_model=List[AllocationTargetRead])
def save_allocation_targets(
    targets: List[AllocationTargetCreate],
    session: Session = Depends(get_session),
):
    total = sum(t.target_percent for t in targets)
    if total > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Total target allocation must be 100% or less, got {total}%",
        )

    result = []
    for target in targets:
        existing = session.exec(
            select(AllocationTarget).where(AllocationTarget.type == target.type)
        ).first()
        if existing:
            existing.target_percent = target.target_percent
            session.add(existing)
            result.append(existing)
        else:
            db_target = AllocationTarget(**target.model_dump())
            session.add(db_target)
            result.append(db_target)
    session.commit()
    for item in result:
        session.refresh(item)
    return result


@router.get("/env-config", response_model=List[Dict[str, Any]])
def list_env_config():
    return get_env_config()


@router.post("/env-config")
def save_env_config(payload: Dict[str, str]):
    try:
        return update_env_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{key}")
def get_setting(key: str, session: Session = Depends(get_session)):
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}
