import logging

from sqlmodel import Session, select

from database import engine
from models import Asset, PriceSnapshot
from services.asset_type_config import is_market_price_type
from services.market_data import MarketDataService

logger = logging.getLogger(__name__)


def _get_or_create_snapshot(session: Session, asset: Asset, data: dict) -> PriceSnapshot | None:
    if not data or not data.get("price") or not data.get("date"):
        return None

    existing = session.exec(
        select(PriceSnapshot).where(
            PriceSnapshot.asset_id == asset.id,
            PriceSnapshot.date == data["date"],
        )
    ).first()
    if existing:
        return existing

    snapshot = PriceSnapshot(
        asset_id=asset.id,
        date=data["date"],
        price=data["price"],
        change=data.get("change"),
        change_percent=data.get("change_percent"),
    )
    session.add(snapshot)
    return snapshot

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    APSCHEDULER_AVAILABLE = False


def update_all_prices():
    from api.alerts import evaluate_notifications

    with Session(engine) as session:
        service = MarketDataService(session)
        assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
        for asset in assets:
            if not is_market_price_type(session, asset.type):
                continue
            data, _ = service.fetch_price_with_warnings(asset)
            if _get_or_create_snapshot(session, asset, data):
                logger.info("scheduler updated %s: %s", asset.symbol, data['price'])
        session.commit()

        try:
            triggered = evaluate_notifications(session)
            if triggered:
                logger.info("scheduler %d price alerts triggered", len(triggered))
        except Exception as e:
            logger.error("scheduler alert evaluation error: %s", e)


def start_scheduler(hour: int = 15, minute: int = 35):
    if not APSCHEDULER_AVAILABLE:
        logger.warning("scheduler APScheduler not installed; skipping")
        return None
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        update_all_prices,
        "cron",
        hour=hour,
        minute=minute,
        id="daily_price_update",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("scheduler daily price update at %02d:%02d", hour, minute)
    return scheduler
