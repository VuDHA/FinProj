from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import AllocationTarget, Setting
from schemas import AllocationTargetCreate, AllocationTargetRead, SettingCreate, SettingRead

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=List[SettingRead])
def list_settings(session: Session = Depends(get_session)):
    return session.exec(select(Setting)).all()


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


@router.get("/{key}")
def get_setting(key: str, session: Session = Depends(get_session)):
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}
