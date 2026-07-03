from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from common.database import get_session
from common.models import Alert, Asset, PriceSnapshot
from common.schemas import AlertCreate, AlertRead, NotificationRead
from services.market.market_data import MarketDataService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _latest_price(session: Session, asset: Asset) -> Optional[float]:
    """Return the best available market price for an asset."""
    snapshot = session.exec(
        select(PriceSnapshot)
        .where(PriceSnapshot.asset_id == asset.id)
        .order_by(PriceSnapshot.date.desc())
    ).first()
    if snapshot and snapshot.price > 0:
        return snapshot.price

    data = MarketDataService(session).fetch_price(asset)
    if data and data.get("price", 0) > 0:
        return data["price"]

    return None


def _build_notification(alert: Alert, asset: Asset, current_price: float) -> Optional[NotificationRead]:
    """Build a notification if the alert condition is met."""
    if alert.value_type == "VALUE":
        if alert.type == "STOP_LOSS":
            triggered = current_price <= alert.value
            message = f"{asset.symbol} đã giảm xuống {current_price:,.0f} (ngưỡng cắt lỗ {alert.value:,.0f})"
        else:
            triggered = current_price >= alert.value
            message = f"{asset.symbol} đã tăng lên {current_price:,.0f} (ngưỡng chốt lời {alert.value:,.0f})"
    elif alert.value_type == "PERCENT":
        if alert.reference_price is None or alert.reference_price <= 0:
            return None
        if alert.type == "STOP_LOSS":
            target = alert.reference_price * (1 - alert.value / 100)
            triggered = current_price <= target
            message = f"{asset.symbol} đã giảm {alert.value}% xuống {current_price:,.0f} (ngưỡng {target:,.0f})"
        else:
            target = alert.reference_price * (1 + alert.value / 100)
            triggered = current_price >= target
            message = f"{asset.symbol} đã tăng {alert.value}% lên {current_price:,.0f} (ngưỡng {target:,.0f})"
    else:
        return None

    if not triggered:
        return None

    return NotificationRead(
        id=alert.id,
        asset_id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        type=alert.type,
        value_type=alert.value_type,
        value=alert.value,
        reference_price=alert.reference_price,
        current_price=current_price,
        message=message,
    )


@router.post("/", response_model=AlertRead)
def create_alert(alert: AlertCreate, session: Session = Depends(get_session)):
    asset = session.get(Asset, alert.asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")

    if alert.type not in ("STOP_LOSS", "TAKE_PROFIT"):
        raise HTTPException(status_code=400, detail="Type must be STOP_LOSS or TAKE_PROFIT")

    if alert.value_type not in ("VALUE", "PERCENT"):
        raise HTTPException(status_code=400, detail="value_type must be VALUE or PERCENT")

    if alert.value <= 0:
        raise HTTPException(status_code=400, detail="value must be positive")

    reference_price = None
    if alert.value_type == "PERCENT":
        reference_price = _latest_price(session, asset)
        if reference_price is None:
            raise HTTPException(
                status_code=400,
                detail="Không thể lấy giá thị trường để tạo cảnh báo phần trăm.",
            )

    db_alert = Alert(
        asset_id=alert.asset_id,
        type=alert.type,
        value_type=alert.value_type,
        value=alert.value,
        reference_price=reference_price,
        is_active=True,
    )
    session.add(db_alert)
    session.commit()
    session.refresh(db_alert)

    return AlertRead(
        id=db_alert.id,
        asset_id=db_alert.asset_id,
        symbol=asset.symbol,
        name=asset.name,
        type=db_alert.type,
        value_type=db_alert.value_type,
        value=db_alert.value,
        reference_price=db_alert.reference_price,
        is_active=db_alert.is_active,
        created_at=db_alert.created_at,
        resolved_at=db_alert.resolved_at,
    )


@router.get("/", response_model=List[AlertRead])
def list_alerts(session: Session = Depends(get_session)):
    alerts = session.exec(select(Alert).order_by(Alert.created_at.desc())).all()
    result = []
    for alert in alerts:
        asset = session.get(Asset, alert.asset_id)
        result.append(
            AlertRead(
                id=alert.id,
                asset_id=alert.asset_id,
                symbol=asset.symbol if asset else None,
                name=asset.name if asset else None,
                type=alert.type,
                value_type=alert.value_type,
                value=alert.value,
                reference_price=alert.reference_price,
                is_active=alert.is_active,
                created_at=alert.created_at,
                resolved_at=alert.resolved_at,
            )
        )
    return result


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, session: Session = Depends(get_session)):
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    session.delete(alert)
    session.commit()
    return {"ok": True}


def evaluate_notifications(session: Session) -> List[NotificationRead]:
    """Evaluate active alerts against current market prices and return triggered notifications."""
    active_alerts = session.exec(select(Alert).where(Alert.is_active == True)).all()
    notifications: List[NotificationRead] = []
    for alert in active_alerts:
        asset = session.get(Asset, alert.asset_id)
        if not asset or not asset.is_active:
            continue

        current_price = _latest_price(session, asset)
        if current_price is None:
            continue

        notification = _build_notification(alert, asset, current_price)
        if notification:
            notifications.append(notification)

    return notifications


@router.get("/notifications", response_model=List[NotificationRead])
def get_notifications(session: Session = Depends(get_session)):
    return evaluate_notifications(session)


@router.post("/{alert_id}/resolve", response_model=AlertRead)
def resolve_alert(alert_id: int, session: Session = Depends(get_session)):
    alert = session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_active = False
    alert.resolved_at = datetime.utcnow()
    session.commit()
    session.refresh(alert)

    asset = session.get(Asset, alert.asset_id)
    return AlertRead(
        id=alert.id,
        asset_id=alert.asset_id,
        symbol=asset.symbol if asset else None,
        name=asset.name if asset else None,
        type=alert.type,
        value_type=alert.value_type,
        value=alert.value,
        reference_price=alert.reference_price,
        is_active=alert.is_active,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )
