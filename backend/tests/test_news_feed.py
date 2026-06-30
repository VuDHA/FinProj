import datetime

from models import Asset, NewsAlert, NewsArticle, NewsSource, NewsSymbol, Watchlist
from services.news.feed import NewsFeedService


def _create_source(session, code="cafef", name="CafeF"):
    source = NewsSource(code=code, name=name, source_type="rss", language="vi")
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def _create_article(session, source, title, symbols=None, sentiment=0.0, impact=0.0, hours_ago=1, language="vi"):
    article = NewsArticle(
        source_id=source.id,
        url=f"https://example.com/{title.replace(' ', '-')}",
        title=title,
        summary="summary",
        published_at=datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago),
        sentiment_score=sentiment,
        impact_score=impact,
        language=language,
    )
    session.add(article)
    session.commit()
    session.refresh(article)
    for symbol in symbols or []:
        session.add(NewsSymbol(article_id=article.id, symbol=symbol))
    session.commit()
    return article


def test_list_articles(session):
    source = _create_source(session)
    _create_article(session, source, "Tin FPT", symbols=["FPT"])
    service = NewsFeedService(session)
    articles = service.list_articles(symbol="FPT")
    assert len(articles) == 1
    assert articles[0].title == "Tin FPT"


def test_personalized_feed_with_watchlist(session):
    source = _create_source(session)
    _create_article(session, source, "Tin HPG", symbols=["HPG"])
    _create_article(session, source, "Tin VIC", symbols=["VIC"])
    session.add(Watchlist(symbol="HPG"))
    session.commit()
    service = NewsFeedService(session)
    articles = service.personalized_feed(include_portfolio=False, include_watchlist=True)
    assert len(articles) == 1
    assert "HPG" in service.get_article_symbols(articles[0].id)


def test_personalized_feed_with_portfolio(session):
    source = _create_source(session)
    _create_article(session, source, "Tin VCB", symbols=["VCB"])
    asset = Asset(symbol="VCB", name="Vietcombank", type="STOCK", currency="VND")
    session.add(asset)
    session.commit()
    service = NewsFeedService(session)
    articles = service.personalized_feed(include_portfolio=True, include_watchlist=False)
    assert len(articles) == 1


def test_trending(session):
    source = _create_source(session)
    _create_article(session, source, "Tin HPG 1", symbols=["HPG"], impact=0.8)
    _create_article(session, source, "Tin HPG 2", symbols=["HPG"], impact=0.5)
    _create_article(session, source, "Tin FPT", symbols=["FPT"], impact=0.2)
    service = NewsFeedService(session)
    trending = service.trending(hours=24, limit=10)
    assert trending["symbols"][0]["symbol"] == "HPG"
    assert trending["symbols"][0]["mentions"] == 2


def test_daily_brief(session):
    source = _create_source(session)
    _create_article(session, source, "Tin quan trọng", symbols=["VHM"], impact=0.9)
    service = NewsFeedService(session)
    brief = service.daily_brief()
    assert brief["total_articles"] >= 1
    assert brief["top_articles"][0].title == "Tin quan trọng"


def test_daily_brief_scope(session):
    vn_source = _create_source(session, code="cafef", name="CafeF")
    global_source = _create_source(session, code="yahoo", name="Yahoo")
    _create_article(session, vn_source, "Tin VN", symbols=["VHM"], impact=0.9)
    _create_article(session, global_source, "Global news", symbols=["AAPL"], impact=0.9, language="en")
    service = NewsFeedService(session)
    assert service.daily_brief(scope="vn")["total_articles"] == 1
    assert service.daily_brief(scope="global")["total_articles"] == 1
    assert service.daily_brief(scope="vn")["top_articles"][0].title == "Tin VN"
    assert service.daily_brief(scope="global")["top_articles"][0].title == "Global news"
