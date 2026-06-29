from sqlmodel import Session, select

from database import engine
from models import Asset, PriceSnapshot
from services.market_data import MarketDataService


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
    with Session(engine) as session:
        service = MarketDataService(session)
        assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
        for asset in assets:
            data, _ = service.fetch_price_with_warnings(asset)
            if _get_or_create_snapshot(session, asset, data):
                print(f"[scheduler] updated {asset.symbol}: {data['price']}")
        session.commit()


def start_scheduler(hour: int = 15, minute: int = 35):
    if not APSCHEDULER_AVAILABLE:
        print("[scheduler] APScheduler not installed; skipping")
        return None
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        update_all_prices,
        "cron",
        hour=hour,
        minute=minute,
        id="daily_price_update",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[scheduler] daily price update at {hour:02d}:{minute:02d}")
    return scheduler
