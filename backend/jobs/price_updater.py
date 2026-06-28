from sqlmodel import Session, select

from database import engine
from models import Asset, PriceSnapshot
from services.market_data import MarketDataService

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    APSCHEDULER_AVAILABLE = False


def update_all_prices():
    with Session(engine) as session:
        service = MarketDataService()
        assets = session.exec(select(Asset).where(Asset.is_active == True)).all()
        for asset in assets:
            data = service.fetch_price(asset)
            if data:
                snapshot = PriceSnapshot(asset_id=asset.id, **data)
                session.add(snapshot)
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
