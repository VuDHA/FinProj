import json
from typing import Dict, Optional

from sqlmodel import Session, select

from models import Asset, Setting
from services.asset_type_config import get_asset_types
from services.sources import registry


DEFAULT_SOURCES: Dict[str, str] = {
    "STOCK": "kbs",
    "FUND": "fmarket",
    "ETF": "kbs",
    "GOLD": "vangtoday",
    "CRYPTO": "coingecko",
}

_SETTING_KEY_PREFIX = "default_source"


def _key(asset_type: str) -> str:
    return f"{_SETTING_KEY_PREFIX}:{asset_type.upper()}"


def _market_types(session: Session) -> set:
    return {
        code
        for code, info in get_asset_types(session).items()
        if info.get("marketPrice", True)
    }


def get_default_sources(session: Session) -> Dict[str, str]:
    """Return the current default source for each market-priced asset type."""
    result = {code: source for code, source in DEFAULT_SOURCES.items()}
    for asset_type in _market_types(session):
        if asset_type not in result:
            result[asset_type] = DEFAULT_SOURCES.get(asset_type, "kbs")
        setting = session.exec(select(Setting).where(Setting.key == _key(asset_type))).first()
        if setting and setting.value:
            result[asset_type] = setting.value
    return result


def set_default_sources(session: Session, sources: Dict[str, str]) -> Dict[str, str]:
    """Persist default sources per market-priced asset type. Invalid sources are ignored."""
    valid_types = _market_types(session)
    for asset_type, source in sources.items():
        asset_type = asset_type.upper()
        if asset_type not in valid_types:
            continue
        if source not in [s.code for s in registry.for_type(asset_type)]:
            continue
        key = _key(asset_type)
        setting = session.exec(select(Setting).where(Setting.key == key)).first()
        if setting is None:
            setting = Setting(key=key, value=source)
            session.add(setting)
        else:
            setting.value = source
    session.commit()
    return get_default_sources(session)


def seed_default_sources(session: Session) -> None:
    """Ensure default source settings exist in the database."""
    for asset_type, source in DEFAULT_SOURCES.items():
        key = _key(asset_type)
        if session.exec(select(Setting).where(Setting.key == key)).first() is None:
            session.add(Setting(key=key, value=source))
    session.commit()


def resolve_asset_source(session: Session, asset: Asset) -> str:
    """Return the effective source code for an asset."""
    if asset.source:
        source = registry.get(asset.source)
        if source and asset.type in source.supported_types:
            return asset.source
    defaults = get_default_sources(session)
    return defaults.get(asset.type, DEFAULT_SOURCES.get(asset.type, "kbs"))


def is_valid_source_for_type(source: str, asset_type: str) -> bool:
    source_obj = registry.get(source)
    return source_obj is not None and asset_type in source_obj.supported_types


def get_asset_source_params(asset: Asset) -> Optional[dict]:
    if not asset.source_params:
        return None
    try:
        return json.loads(asset.source_params)
    except Exception:
        return None


def set_asset_source_params(asset: Asset, params: Optional[dict]) -> None:
    asset.source_params = json.dumps(params, ensure_ascii=False) if params else None
