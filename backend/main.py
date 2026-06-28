from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import analytics, assets, backtest, gold_fx, import_export, income, portfolio, prices, rebalance, transactions
from api.settings import router as settings_router
from config import settings
from database import init_db
from jobs.price_updater import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler(settings.SCHEDULER_HOUR, settings.SCHEDULER_MINUTE)
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

app.include_router(assets.router, prefix=settings.API_PREFIX)
app.include_router(prices.router, prefix=settings.API_PREFIX)
app.include_router(transactions.router, prefix=settings.API_PREFIX)
app.include_router(income.router, prefix=settings.API_PREFIX)
app.include_router(portfolio.router, prefix=settings.API_PREFIX)
app.include_router(rebalance.router, prefix=settings.API_PREFIX)
app.include_router(backtest.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(gold_fx.router, prefix=settings.API_PREFIX)
app.include_router(import_export.router, prefix=settings.API_PREFIX)
app.include_router(settings_router, prefix=settings.API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
