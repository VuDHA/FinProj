from sqlmodel import Session

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None
    APSCHEDULER_AVAILABLE = False

from database import engine
from services.news.alerts import AlertService
from services.news.crawler import NewsCrawlerService


def update_news():
    """Background job: crawl news from all sources and generate alerts."""
    try:
        with Session(engine) as session:
            crawler = NewsCrawlerService(session)
            results = crawler.refresh()
            alerts_service = AlertService(session)
            alerts_count = alerts_service.generate_alerts(hours=1)
            total = sum(results.values())
            print(f"[news scheduler] crawled {total} new articles, {alerts_count} alerts")
    except Exception as e:
        print(f"[news scheduler] error: {e}")


def add_news_jobs(scheduler: BackgroundScheduler):
    """Register news-related cron jobs on the shared scheduler."""
    # VN market hours: crawl every 15 minutes from 08:30 to 15:15
    scheduler.add_job(
        update_news,
        "cron",
        hour="8-15",
        minute="*/15",
        id="news_update_vn_hours",
        replace_existing=True,
    )
    # Off-hours: crawl every 30 minutes
    scheduler.add_job(
        update_news,
        "cron",
        hour="16-23,0-7",
        minute="*/30",
        id="news_update_off_hours",
        replace_existing=True,
    )
    print("[news scheduler] registered jobs")
