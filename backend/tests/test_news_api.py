import datetime

from common.models import Asset, NewsArticle, NewsSource, NewsSymbol, Watchlist
from services.news.alerts import AlertService


def _create_source(session, code="cafef", name="CafeF"):
    source = NewsSource(code=code, name=name, source_type="rss", language="vi")
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def _create_article(session, source, title, symbols=None, sentiment=0.0, impact=0.0, hours_ago=1):
    article = NewsArticle(
        source_id=source.id,
        url=f"https://example.com/{title.replace(' ', '-')}",
        title=title,
        summary="summary",
        published_at=datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago),
        sentiment_score=sentiment,
        impact_score=impact,
        language="vi",
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    for symbol in symbols or []:
        session.add(NewsSymbol(article_id=article.id, symbol=symbol))
    session.commit()
    return article


def test_list_news(client, session):
    source = _create_source(session)
    _create_article(session, source, "Tin FPT", symbols=["FPT"])
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Tin FPT"


def test_feed_filter(client, session):
    source = _create_source(session)
    _create_article(session, source, "Tin HPG", symbols=["HPG"])
    session.add(Watchlist(symbol="HPG"))
    session.commit()
    response = client.get("/api/v1/news/feed?portfolio=false&watchlist=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["symbols"] == ["HPG"]


def test_article_detail(client, session):
    source = _create_source(session)
    article = _create_article(session, source, "Tin chi tiết", symbols=["VIC"])
    response = client.get(f"/api/v1/news/{article.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Tin chi tiết"
    assert "VIC" in data["symbols"]


def test_watchlist_crud(client, session):
    response = client.post("/api/v1/news/watchlist", json={"symbol": "FPT", "name": "FPT Corp"})
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "FPT"

    response = client.get("/api/v1/news/watchlist/list")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.delete("/api/v1/news/watchlist/FPT")
    assert response.status_code == 200

    response = client.get("/api/v1/news/watchlist/list")
    assert len(response.json()) == 0


def test_trending(client, session):
    source = _create_source(session)
    _create_article(session, source, "Tin HPG", symbols=["HPG"], impact=0.8)
    response = client.get("/api/v1/news/trending/now")
    assert response.status_code == 200
    data = response.json()
    assert data["symbols"][0]["symbol"] == "HPG"


def test_alerts(client, session):
    source = _create_source(session)
    session.add(Asset(symbol="HPG", name="Hoa Phat", type="STOCK", currency="VND"))
    session.commit()
    _create_article(session, source, "Tin HPG quan trọng", symbols=["HPG"], impact=0.9, hours_ago=0)

    # Exercise the alert generation logic directly; the list endpoint covers serialization.
    AlertService(session).generate_alerts(hours=1)

    alert_response = client.get("/api/v1/news/alerts/list")
    assert alert_response.status_code == 200
    alerts = alert_response.json()
    assert len(alerts) >= 1
    assert alerts[0]["symbol"] == "HPG"
