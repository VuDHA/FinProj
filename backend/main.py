import datetime
import logging
import socket
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session

from api import ai, alerts, analytics, assets, backtest, compare, gold_fx, import_export, income, news, portfolio, prices, rebalance, transactions
from api.settings import router as settings_router
from api.transactions import repair_zero_price_transactions
from config import settings, PROJECT_ROOT
from database import engine, init_db
from jobs.news_updater import add_news_jobs
from jobs.price_updater import start_scheduler
from jobs.backup import add_backup_jobs
from services.logging_config import setup_logging


def _convert_decimal(obj: Any) -> Any:
    """Recursively convert Decimal/date/datetime/UUID values to JSON-safe types.

    Pydantic's python-mode serialization preserves native Python types (Decimal,
    date, datetime, UUID) that stdlib json.dumps cannot encode. We convert them
    the same way Pydantic's json-mode would, but with Decimal -> float instead
    of Decimal -> str.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_decimal(v) for v in obj]
    return obj


# Patch ModelField.serialize AND ModelField.serialize_json at the class level
# so ALL existing ModelField instances (created at route-registration time)
# use the patched versions. FastAPI 0.136 uses a "fast path" that calls
# field.serialize_json() (Pydantic Rust core -> bytes, serializes Decimal as
# string) when no custom response_class is set, and field.serialize() otherwise.
# Patching the class methods ensures every instance resolves through our
# override at call time. We convert Decimal -> float AFTER Pydantic serialization
# to avoid the "Decimal as string" behaviour in JSON responses.
import json

from fastapi._compat import ModelField as _ModelField

_original_serialize = _ModelField.serialize
_original_serialize_json = getattr(_ModelField, "serialize_json", None)


def _decimal_serialize(self: _ModelField, value: Any, *, mode: str = "json", **kwargs: Any) -> Any:
    if mode == "json":
        # Use python mode to preserve Decimal values, then convert to float
        # ourselves. (json mode would already stringify Decimal before we can
        # intercept.)
        result = _original_serialize(self, value, mode="python", **kwargs)
        return _convert_decimal(result)
    return _original_serialize(self, value, mode=mode, **kwargs)


def _decimal_serialize_json(self: _ModelField, value: Any, **kwargs: Any) -> bytes:
    # Avoid the Rust-core fast path (dump_json) which serializes Decimal as
    # string. Instead use the (already-patched) serialize() with mode="json"
    # to get a Python dict with Decimal -> float, then encode to JSON bytes.
    result = self.serialize(value, mode="json", **kwargs)
    return json.dumps(
        result,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


_ModelField.serialize = _decimal_serialize  # type: ignore[method-assign]
# serialize_json was removed in newer pydantic versions; only patch if present.
if _original_serialize_json is not None:
    _ModelField.serialize_json = _decimal_serialize_json  # type: ignore[method-assign]


# Patch jsonable_encoder for endpoints WITHOUT a response_model. When
# response_model is None, FastAPI's serialize_response takes the else branch
# and calls jsonable_encoder(response_content). That function calls
# obj.model_dump(mode="json") for BaseModel instances, which stringifies
# Decimal before we can intercept. We wrap it so BaseModels are dumped in
# python mode (preserving Decimal) and converted to float ourselves.
import fastapi.encoders
import fastapi.routing

_original_jsonable_encoder = fastapi.encoders.jsonable_encoder


def _decimal_jsonable_encoder(obj: Any, *args: Any, **kwargs: Any) -> Any:
    if isinstance(obj, BaseModel):
        dumped = obj.model_dump(
            mode="python",
            include=kwargs.get("include"),
            exclude=kwargs.get("exclude"),
            by_alias=kwargs.get("by_alias", True),
            exclude_unset=kwargs.get("exclude_unset", False),
            exclude_none=kwargs.get("exclude_none", False),
            exclude_defaults=kwargs.get("exclude_defaults", False),
        )
        return _original_jsonable_encoder(_convert_decimal(dumped), *args, **kwargs)
    return _original_jsonable_encoder(obj, *args, **kwargs)


fastapi.encoders.jsonable_encoder = _decimal_jsonable_encoder  # type: ignore[assignment]
fastapi.routing.jsonable_encoder = _decimal_jsonable_encoder  # type: ignore[assignment]


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
        add_backup_jobs(scheduler)
    yield
    if scheduler:
        scheduler.shutdown()


app = FastAPI(
    title="Vietnam Wealth Management",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
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

# Register routers from other agents using try/except so main.py doesn't
# fail if the files don't exist yet.
try:
    from api import goals, dividends, tax
    app.include_router(goals.router, prefix=settings.API_PREFIX)
    app.include_router(dividends.router, prefix=settings.API_PREFIX)
    app.include_router(tax.router, prefix=settings.API_PREFIX)
except ImportError:
    pass
try:
    from api import search
    app.include_router(search.router, prefix=settings.API_PREFIX)
except ImportError:
    pass


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 53))
            return s.getsockname()[0]
    except Exception:
        return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/lan-ip")
def lan_ip():
    return {"ip": get_lan_ip()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
