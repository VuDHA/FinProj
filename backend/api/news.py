import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import NewsAlert, NewsArticle, NewsSymbol, Watchlist
from schemas import (
    AlertRead,
    ArticleListResponse,
    ArticleRead,
    DailyBriefResponse,
    RefreshResponse,
    TrendingResponse,
    TrendingSymbol,
    WatchlistCreate,
    WatchlistItem,
)
from services.news.alerts import AlertService
from services.news.crawler import NewsCrawlerService
from services.news.dictionaries import impact_label, sentiment_label
from services.news.feed import NewsFeedService

router = APIRouter(prefix="/news", tags=["news"])


def _article_to_schema(article: NewsArticle, symbols: Optional[List[str]] = None) -> ArticleRead:
    return ArticleRead(
        id=article.id,
        source_id=article.source_id,
        url=article.url,
        title=article.title,
        summary=article.summary,
        author=article.author,
        category=article.category,
        tags=article.tags,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        sentiment_score=article.sentiment_score,
        impact_score=article.impact_score,
        language=article.language,
        symbols=symbols or [],
        sentiment_label=sentiment_label(article.sentiment_score),
        impact_label=impact_label(article.impact_score),
    )


def _load_article_symbols(session: Session, article_ids: List[int]) -> dict:
    rows = session.exec(
        select(NewsSymbol.article_id, NewsSymbol.symbol).where(
            NewsSymbol.article_id.in_(article_ids)
        )
    ).all()
    mapping = {}
    for article_id, symbol in rows:
        mapping.setdefault(article_id, []).append(symbol)
    return mapping


@router.get("", response_model=ArticleListResponse)
def list_news(
    symbol: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None),
    sentiment: Optional[str] = Query(None, pattern="^(positive|negative|neutral)$"),
    min_impact: Optional[float] = Query(None, ge=0, le=1),
    search: Optional[str] = Query(None),
    date_from: Optional[datetime.date] = Query(None),
    date_to: Optional[datetime.date] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    articles = service.list_articles(
        symbol=symbol,
        source_id=source_id,
        sentiment=sentiment,
        min_impact=min_impact,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    article_ids = [a.id for a in articles]
    symbol_map = _load_article_symbols(session, article_ids)

    total = session.exec(
        select(func.count(NewsArticle.id)).where(NewsArticle.is_active == True)
    ).one()

    return ArticleListResponse(
        items=[_article_to_schema(a, symbol_map.get(a.id, [])) for a in articles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/feed", response_model=ArticleListResponse)
def personalized_feed(
    portfolio: bool = Query(True),
    watchlist: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    articles = service.personalized_feed(
        include_portfolio=portfolio,
        include_watchlist=watchlist,
        limit=limit,
        offset=offset,
    )
    article_ids = [a.id for a in articles]
    symbol_map = _load_article_symbols(session, article_ids)
    return ArticleListResponse(
        items=[_article_to_schema(a, symbol_map.get(a.id, [])) for a in articles],
        total=len(articles),
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, session: Session = Depends(get_session)):
    service = NewsFeedService(session)
    article = service.get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    symbols = service.get_article_symbols(article_id)
    return _article_to_schema(article, symbols)


@router.get("/trending/now", response_model=TrendingResponse)
def trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    data = service.trending(hours=hours, limit=limit)
    return TrendingResponse(
        symbols=[TrendingSymbol(symbol=item["symbol"], mentions=item["mentions"]) for item in data["symbols"]],
        sentiment=data["sentiment"],
    )


@router.get("/brief/daily", response_model=DailyBriefResponse)
def daily_brief(
    hours: int = Query(24, ge=1, le=168),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    data = service.daily_brief(hours=hours)
    article_ids = [a.id for a in data["top_articles"]]
    symbol_map = _load_article_symbols(session, article_ids)
    return DailyBriefResponse(
        generated_at=data["generated_at"],
        period_hours=data["period_hours"],
        total_articles=data["total_articles"],
        top_articles=[
            _article_to_schema(a, symbol_map.get(a.id, [])) for a in data["top_articles"]
        ],
        key_symbols=data["key_symbols"],
    )


@router.get("/alerts/list", response_model=List[AlertRead])
def list_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    service = AlertService(session)
    alerts = service.list_alerts(unread_only=unread_only, limit=limit)
    return [
        AlertRead(
            id=a.id,
            alert_type=a.alert_type,
            symbol=a.symbol,
            article_id=a.article_id,
            title=a.title,
            message=a.message,
            is_read=a.is_read,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(alert_id: int, session: Session = Depends(get_session)):
    service = AlertService(session)
    alert = service.mark_read(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Cảnh báo không tồn tại")
    return AlertRead(
        id=alert.id,
        alert_type=alert.alert_type,
        symbol=alert.symbol,
        article_id=alert.article_id,
        title=alert.title,
        message=alert.message,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )


@router.get("/alerts/unread-count")
def unread_alert_count(session: Session = Depends(get_session)):
    service = AlertService(session)
    return {"count": service.unread_count()}


@router.get("/watchlist/list", response_model=List[WatchlistItem])
def list_watchlist(session: Session = Depends(get_session)):
    items = session.exec(select(Watchlist).order_by(Watchlist.added_at.desc())).all()
    return [
        WatchlistItem(
            id=w.id,
            symbol=w.symbol,
            name=w.name,
            notes=w.notes,
            added_at=w.added_at,
        )
        for w in items
    ]


@router.post("/watchlist", response_model=WatchlistItem)
def add_watchlist(
    payload: WatchlistCreate,
    session: Session = Depends(get_session),
):
    symbol = payload.symbol.strip().upper()
    existing = session.exec(select(Watchlist).where(Watchlist.symbol == symbol)).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} đã có trong watchlist")
    item = Watchlist(symbol=symbol, name=payload.name, notes=payload.notes)
    session.add(item)
    session.commit()
    session.refresh(item)
    return WatchlistItem(
        id=item.id,
        symbol=item.symbol,
        name=item.name,
        notes=item.notes,
        added_at=item.added_at,
    )


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str, session: Session = Depends(get_session)):
    item = session.exec(select(Watchlist).where(Watchlist.symbol == symbol.upper())).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Mã không tồn tại trong watchlist")
    session.delete(item)
    session.commit()
    return {"ok": True}


@router.post("/refresh", response_model=RefreshResponse)
def refresh_news(
    source: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    crawler = NewsCrawlerService(session)
    results = crawler.refresh(source_code=source)
    alerts_service = AlertService(session)
    alerts_count = alerts_service.generate_alerts(hours=1)
    return RefreshResponse(results=results, alerts_generated=alerts_count)
