from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Setting
from schemas import SettingCreate, SettingRead

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


@router.get("/{key}")
def get_setting(key: str, session: Session = Depends(get_session)):
    setting = session.exec(select(Setting).where(Setting.key == key)).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}
