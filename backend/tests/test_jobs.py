import datetime

from models import Asset, NewsArticle, NewsSource, NewsSymbol
from services.news.alerts import AlertService
from sqlmodel import Session, select


class _SessionWrapper:
    """Yield the fixture session so background jobs can use the same DB session."""

    def __init__(self, engine, session):
        self._engine = engine
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def _wrap_session(module, session):
    module.Session = lambda engine: _SessionWrapper(engine, session)


def test_update_news_job(session, monkeypatch):
    from jobs import news_updater

    _wrap_session(news_updater, session)

    monkeypatch.setattr(
        "services.news.crawler.NewsCrawlerService.refresh",
        lambda self, source_code=None: {"test": 1},
    )

    source = NewsSource(code="cafef", name="CafeF", source_type="rss", language="vi")
    session.add(source)
    session.commit()
    session.refresh(source)

    asset = Asset(symbol="HPG", name="Hoa Phat", type="STOCK", currency="VND")
    session.add(asset)
    session.commit()
    session.refresh(asset)

    article = NewsArticle(
        source_id=source.id,
        url="https://example.com/hpg",
        title="Tin HPG",
        summary="summary",
        published_at=datetime.datetime.utcnow(),
        impact_score=0.9,
        language="vi",
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    session.add(NewsSymbol(article_id=article.id, symbol="HPG"))
    session.commit()

    news_updater.update_news()

    alerts = AlertService(session).list_alerts(limit=10)
    assert len(alerts) >= 1


def test_update_all_prices_job(session, monkeypatch):
    from jobs import price_updater

    _wrap_session(price_updater, session)

    today = datetime.date.today()
    asset = Asset(symbol="VCB", name="Vietcombank", type="STOCK", currency="VND")
    session.add(asset)
    session.commit()
    session.refresh(asset)

    monkeypatch.setattr(
        "services.market_data.MarketDataService.fetch_price_with_warnings",
        lambda self, asset: ({"price": 100, "change": 1, "change_percent": 1, "date": today}, []),
    )

    price_updater.update_all_prices()

    snapshot = session.exec(
        select(price_updater.PriceSnapshot).where(
            price_updater.PriceSnapshot.asset_id == asset.id
        )
    ).first()
    assert snapshot is not None
    assert snapshot.price == 100


def test_start_price_scheduler():
    from jobs import price_updater

    scheduler = price_updater.start_scheduler(hour=15, minute=35)
    assert scheduler is not None
    job = scheduler.get_job("daily_price_update")
    assert job is not None
    scheduler.shutdown(wait=False)
