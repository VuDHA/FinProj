from sqlmodel import Session

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None
    APSCHEDULER_AVAILABLE = False

from common.database import engine
from services.news.alerts import AlertService
from services.news.crawler import NewsCrawlerService


def _refresh_region(region: str, generate_alerts: bool = True):
    """Crawl one region and optionally generate alerts."""
    try:
        with Session(engine) as session:
            crawler = NewsCrawlerService(session)
            results = crawler.crawl_region(region)
            alerts_count = 0
            if generate_alerts:
                alerts_service = AlertService(session)
                alerts_count = alerts_service.generate_alerts(hours=1)
            total = sum(results.values())
            print(f"[news scheduler] {region}: crawled {total} new articles, {alerts_count} alerts")
    except Exception as e:
        print(f"[news scheduler] {region} error: {e}")


def update_vn_news():
    """Background job: crawl VN news sources and generate alerts."""
    _refresh_region("vn", generate_alerts=True)


def update_global_news():
    """Background job: crawl global news sources (no VN alerts)."""
    _refresh_region("global", generate_alerts=False)


def add_news_jobs(scheduler: BackgroundScheduler):
    """Register news-related cron jobs on the shared scheduler."""
    # VN market hours: crawl every 15 minutes from 08:30 to 15:15
    scheduler.add_job(
        update_vn_news,
        "cron",
        hour="8-15",
        minute="*/15",
        id="news_update_vn_hours",
        replace_existing=True,
    )
    # VN off-hours: crawl every 30 minutes
    scheduler.add_job(
        update_vn_news,
        "cron",
        hour="16-23,0-7",
        minute="*/30",
        id="news_update_off_hours",
        replace_existing=True,
    )
    # Global news: slower cadence, every 30 minutes
    scheduler.add_job(
        update_global_news,
        "cron",
        minute="*/30",
        id="news_update_global",
        replace_existing=True,
    )
    print("[news scheduler] registered jobs")
