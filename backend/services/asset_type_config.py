import datetime
import json
import re
import uuid
from decimal import Decimal
from typing import Dict, List

from sqlmodel import Session, select

from models import Asset, PriceSnapshot, Setting, Transaction


SETTING_KEY = "asset_types"

FIELD_OPTIONS = ["symbol", "name", "exchange", "currency", "source", "value"]

# capitalMode values:
#   "unit_price"  — capital = quantity × price (default, backward compatible)
#   "total_value" — capital = entered price; current value = quantity × latest per-unit price
CAPITAL_MODE_UNIT_PRICE = "unit_price"
CAPITAL_MODE_TOTAL_VALUE = "total_value"
CAPITAL_MODES = [CAPITAL_MODE_UNIT_PRICE, CAPITAL_MODE_TOTAL_VALUE]

DEFAULT_ASSET_TYPES: Dict[str, dict] = {
    "STOCK": {"label": "Cổ phiếu", "fields": ["symbol", "name", "exchange", "currency", "source"], "marketPrice": True, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": True},
    "FUND": {"label": "Quỹ", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": True},
    "ETF": {"label": "ETF", "fields": ["symbol", "name", "exchange", "currency", "source"], "marketPrice": True, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": True},
    "GOLD": {"label": "Vàng", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": True},
    "CRYPTO": {"label": "Crypto", "fields": ["symbol", "name", "currency", "source"], "marketPrice": True, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": True},
    "REAL_ESTATE": {"label": "Bất động sản", "fields": ["name", "value"], "marketPrice": False, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": False},
    "LIFE_INSURANCE": {"label": "Bảo hiểm nhân thọ", "fields": ["name", "value"], "marketPrice": False, "capitalMode": CAPITAL_MODE_UNIT_PRICE, "showPnl": False},
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
    """Persist and return a cleaned asset type config.

    When marketPrice or capitalMode changes for an existing type, snapshots for
    all active assets of that type are rebuilt so portfolio calculations stay
    consistent with the new config.
    """
    old_config = get_asset_types(session)

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
        capital_mode = info.get("capitalMode", CAPITAL_MODE_UNIT_PRICE)
        if capital_mode not in CAPITAL_MODES:
            capital_mode = CAPITAL_MODE_UNIT_PRICE
        # total_value mode only makes sense for non-market assets.
        if market_price and capital_mode == CAPITAL_MODE_TOTAL_VALUE:
            capital_mode = CAPITAL_MODE_UNIT_PRICE
        show_pnl = bool(info.get("showPnl", market_price))
        cleaned[code] = {"label": label, "fields": fields, "marketPrice": market_price, "capitalMode": capital_mode, "showPnl": show_pnl}

    value = json.dumps(cleaned, ensure_ascii=False)
    setting = session.exec(select(Setting).where(Setting.key == SETTING_KEY)).first()
    if setting is None:
        setting = Setting(key=SETTING_KEY, value=value)
        session.add(setting)
    else:
        setting.value = value
    session.commit()

    # Detect config changes and rebuild snapshots for affected assets.
    changed_types = _detect_config_changes(old_config, cleaned)
    for code in changed_types:
        _rebuild_snapshots_for_type(session, code, cleaned[code])

    return cleaned


def _detect_config_changes(old: Dict[str, dict], new: Dict[str, dict]) -> List[str]:
    """Return asset type codes whose marketPrice or capitalMode changed."""
    changed = []
    for code, new_info in new.items():
        old_info = old.get(code)
        if old_info is None:
            continue  # new type, no existing assets to rebuild
        if old_info.get("marketPrice") != new_info.get("marketPrice"):
            changed.append(code)
        elif old_info.get("capitalMode") != new_info.get("capitalMode"):
            changed.append(code)
        elif old_info.get("showPnl") != new_info.get("showPnl"):
            changed.append(code)
    return changed


def _rebuild_snapshots_for_type(session: Session, asset_type: str, config: dict) -> None:
    """Rebuild PriceSnapshots for all active assets of the given type.

    - Non-market assets: snapshot is rebuilt from the latest transaction.
      For total_value mode, the per-unit price (price / quantity) is stored.
    - Market assets: old manual snapshots are cleared; the next portfolio
      request or scheduler run will fetch fresh market prices.
    """
    assets = session.exec(
        select(Asset).where(Asset.type == asset_type, Asset.is_active == True)
    ).all()
    if not assets:
        return

    is_market = config.get("marketPrice", True)
    is_total_value = config.get("capitalMode") == CAPITAL_MODE_TOTAL_VALUE

    for asset in assets:
        if not is_market:
            # Rebuild from latest transaction.
            latest_tx = session.exec(
                select(Transaction)
                .where(Transaction.asset_id == asset.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
            ).first()
            if latest_tx:
                snapshot_price = latest_tx.price
                if is_total_value and latest_tx.quantity > 0:
                    snapshot_price = latest_tx.price / latest_tx.quantity
                for snap in session.exec(
                    select(PriceSnapshot).where(PriceSnapshot.asset_id == asset.id)
                ).all():
                    session.delete(snap)
                session.add(
                    PriceSnapshot(
                        asset_id=asset.id,
                        date=datetime.date.today(),
                        price=snapshot_price,
                    )
                )
        else:
            # Switched to market-priced: clear manual snapshots so stale
            # manual values don't override the next market fetch.
            for snap in session.exec(
                select(PriceSnapshot).where(PriceSnapshot.asset_id == asset.id)
            ).all():
                session.delete(snap)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise


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


def get_capital_mode(session: Session, asset_type: str) -> str:
    """Return the capital calculation mode for an asset type.

    'unit_price'  — capital = quantity × price (default)
    'total_value' — capital = entered price; current value = quantity × per-unit price
    """
    return get_asset_types(session).get(asset_type.upper(), {}).get("capitalMode", CAPITAL_MODE_UNIT_PRICE)


def is_total_value_type(session: Session, asset_type: str) -> bool:
    """True when the asset type uses total-value capital mode."""
    return get_capital_mode(session, asset_type) == CAPITAL_MODE_TOTAL_VALUE


def shows_pnl_type(session: Session, asset_type: str) -> bool:
    """True when the asset type should be included in PnL calculations and displays.

    Market-priced assets always show PnL. Non-market assets show PnL only when
    their config has showPnl=true (e.g. brand-priced items like jewelry/diamonds
    whose value changes over time).
    """
    info = get_asset_types(session).get(asset_type.upper(), {})
    if info.get("marketPrice", True):
        return True
    return bool(info.get("showPnl", False))


def get_asset_fields(session: Session, asset_type: str) -> List[str]:
    return get_asset_types(session).get(asset_type.upper(), {}).get("fields", ["symbol", "name"])


def generate_symbol(name: str, asset_type: str) -> str:
    """Generate a unique internal symbol for assets that do not need a human ticker."""
    base = f"{asset_type.lower().replace('_', '-')}-{_slugify(name)}"
    return f"{base}-{uuid.uuid4().hex[:6]}"
