import json
import re
import uuid
from typing import Dict, List

from sqlmodel import Session, select

from common.models import Setting


SETTING_KEY = "asset_types"

FIELD_OPTIONS = ["symbol", "name", "exchange", "currency", "source", "value"]

DEFAULT_ASSET_TYPES: Dict[str, dict] = {
    "STOCK": {"label": "Cổ phiếu", "fields": ["symbol", "name", "exchange", "currency", "source"], "marketPrice": True},
    "FUND": {"label": "Quỹ", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True},
    "ETF": {"label": "ETF", "fields": ["symbol", "name", "exchange", "currency", "source"], "marketPrice": True},
    "GOLD": {"label": "Vàng", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True},
    "CRYPTO": {"label": "Crypto", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True},
    "REAL_ESTATE": {"label": "Bất động sản", "fields": ["name", "value"], "marketPrice": False},
    "LIFE_INSURANCE": {"label": "Bảo hiểm nhân thọ", "fields": ["name", "value"], "marketPrice": False},
}


def _slugify(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:40]


def get_asset_types(session: Session) -> Dict[str, dict]:
    """Return the persisted asset type config, or the defaults if none exists."""
    setting = session.exec(select(Setting).where(Setting.key == SETTING_KEY)).first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            pass
    return dict(DEFAULT_ASSET_TYPES)


def save_asset_types(session: Session, config: Dict[str, dict]) -> Dict[str, dict]:
    """Persist and return a cleaned asset type config."""
    cleaned: Dict[str, dict] = {}
    for code, info in config.items():
        code = str(code).upper().strip()
        if not code:
            continue
        label = str(info.get("label") or code).strip()
        fields = info.get("fields", [])
        if not isinstance(fields, list):
            fields = []
        fields = [f for f in fields if f in FIELD_OPTIONS]
        if "name" not in fields:
            fields = ["name", *fields]
        market_price = bool(info.get("marketPrice", True))
        if not market_price and "value" not in fields:
            fields.append("value")
        cleaned[code] = {"label": label, "fields": fields, "marketPrice": market_price}

    value = json.dumps(cleaned, ensure_ascii=False)
    setting = session.exec(select(Setting).where(Setting.key == SETTING_KEY)).first()
    if setting is None:
        setting = Setting(key=SETTING_KEY, value=value)
        session.add(setting)
    else:
        setting.value = value
    session.commit()
    return cleaned


def seed_asset_types(session: Session) -> None:
    """Ensure the default asset type config exists in the database."""
    existing = session.exec(select(Setting).where(Setting.key == SETTING_KEY)).first()
    if existing is None:
        session.add(Setting(key=SETTING_KEY, value=json.dumps(DEFAULT_ASSET_TYPES, ensure_ascii=False)))
        session.commit()


def get_asset_type_codes(session: Session) -> List[str]:
    return list(get_asset_types(session).keys())


def is_valid_asset_type(session: Session, asset_type: str) -> bool:
    return asset_type.upper() in get_asset_types(session)


def is_market_price_type(session: Session, asset_type: str) -> bool:
    return get_asset_types(session).get(asset_type.upper(), {}).get("marketPrice", True)


def get_asset_fields(session: Session, asset_type: str) -> List[str]:
    return get_asset_types(session).get(asset_type.upper(), {}).get("fields", ["symbol", "name"])


def generate_symbol(name: str, asset_type: str) -> str:
    """Generate a unique internal symbol for assets that do not need a human ticker."""
    base = f"{asset_type.lower().replace('_', '-')}-{_slugify(name)}"
    return f"{base}-{uuid.uuid4().hex[:6]}"
