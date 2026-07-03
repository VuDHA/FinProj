import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from api import ai, alerts, analytics, assets, backtest, compare, gold_fx, import_export, income, news, portfolio, prices, rebalance, transactions
from api.settings import router as settings_router
from api.transactions import repair_zero_price_transactions
from config import settings, PROJECT_ROOT
from database import engine, init_db
from jobs.news_updater import add_news_jobs
from jobs.price_updater import start_scheduler
from services.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(PROJECT_ROOT)
    logger = logging.getLogger(__name__)
    logger.info("Application startup")
    init_db()
    with Session(engine) as session:
        repaired = repair_zero_price_transactions(session)
        if repaired:
            logger.info("Repaired %d zero-price BUY transactions", repaired)
    scheduler = start_scheduler(settings.SCHEDULER_HOUR, settings.SCHEDULER_MINUTE)
    if scheduler:
        add_news_jobs(scheduler)
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(
    title="Vietnam Wealth Management",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router, prefix=settings.API_PREFIX)
app.include_router(alerts.router, prefix=settings.API_PREFIX)
app.include_router(assets.router, prefix=settings.API_PREFIX)
app.include_router(prices.router, prefix=settings.API_PREFIX)
app.include_router(transactions.router, prefix=settings.API_PREFIX)
app.include_router(income.router, prefix=settings.API_PREFIX)
app.include_router(portfolio.router, prefix=settings.API_PREFIX)
app.include_router(rebalance.router, prefix=settings.API_PREFIX)
app.include_router(backtest.router, prefix=settings.API_PREFIX)
app.include_router(compare.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(gold_fx.router, prefix=settings.API_PREFIX)
app.include_router(import_export.router, prefix=settings.API_PREFIX)
app.include_router(news.router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
