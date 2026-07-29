import logging

from sqlmodel import Session

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None
    APSCHEDULER_AVAILABLE = False

from config import settings
from database import engine
from services.news.alerts import AlertService
from services.news.crawler import NewsCrawlerService

logger = logging.getLogger(__name__)


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
            logger.info("news scheduler %s: crawled %d new articles, %d alerts", region, total, alerts_count)
    except Exception as e:
        logger.error("news scheduler %s error: %s", region, e)


def update_vn_news():
    """Background job: crawl VN news sources and generate alerts."""
    _refresh_region("vn", generate_alerts=True)


def update_global_news():
    """Background job: crawl global news sources (no VN alerts)."""
    _refresh_region("global", generate_alerts=False)


def add_news_jobs(scheduler: BackgroundScheduler):
    """Register news-related cron jobs on the shared scheduler."""
    if not settings.NEWS_SCHEDULER_ENABLED:
        logger.info("news scheduler disabled by settings")
        return

    vn_market_interval = max(1, settings.NEWS_VN_MARKET_INTERVAL_MINUTES)
    vn_off_hours_interval = max(1, settings.NEWS_VN_OFF_HOURS_INTERVAL_MINUTES)
    global_interval = max(1, settings.NEWS_GLOBAL_INTERVAL_MINUTES)

    # VN market hours: crawl every N minutes from 08:30 to 15:15
    scheduler.add_job(
        update_vn_news,
        "cron",
        hour="8-15",
        minute=f"*/{vn_market_interval}",
        id="news_update_vn_hours",
        replace_existing=True,
        max_instances=1,
    )
    # VN off-hours: crawl every N minutes
    scheduler.add_job(
        update_vn_news,
        "cron",
        hour="16-23,0-7",
        minute=f"*/{vn_off_hours_interval}",
        id="news_update_off_hours",
        replace_existing=True,
        max_instances=1,
    )
    # Global news: slower cadence, every N minutes
    scheduler.add_job(
        update_global_news,
        "cron",
        minute=f"*/{global_interval}",
        id="news_update_global",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "news scheduler registered jobs: vn_market=%dmin, vn_off_hours=%dmin, global=%dmin",
        vn_market_interval, vn_off_hours_interval, global_interval,
    )
