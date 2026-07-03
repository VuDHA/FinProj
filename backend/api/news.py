import asyncio
import datetime
import json
import threading
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlmodel import Session, select

from config import Settings
from database import get_session
from models import NewsAlert, NewsArticle, NewsSource, NewsSymbol, Watchlist
from schemas import (
    AiSummaryRequest,
    AiSummaryResponse,
    AlertRead,
    ArticleListResponse,
    ArticleRead,
    DailyBriefResponse,
    NewsSourceRead,
    TrendingResponse,
    TrendingSymbol,
    WatchlistCreate,
    WatchlistItem,
)
from services.news.ai import NewsAI
from services.news.alerts import AlertService
from services.news.crawler import NewsCrawlerService
from services.news.refresh_tracker import RefreshTracker
from services.news.dictionaries import impact_label, sentiment_label
from services.news.feed import NewsFeedService
from services.rag_context import RagContextService

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
        relevance_score=article.relevance_score,
        is_standout=article.is_standout,
        language=article.language,
        region=article.region,
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
    tag: Optional[str] = Query(None),
    date_from: Optional[datetime.date] = Query(None),
    date_to: Optional[datetime.date] = Query(None),
    region: Optional[str] = Query("vn", pattern="^(vn|global)$"),
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
        tag=tag,
        date_from=date_from,
        date_to=date_to,
        region=region,
        limit=limit,
        offset=offset,
    )
    article_ids = [a.id for a in articles]
    symbol_map = _load_article_symbols(session, article_ids)

    total = service.count_articles(
        symbol=symbol,
        source_id=source_id,
        sentiment=sentiment,
        min_impact=min_impact,
        search=search,
        tag=tag,
        date_from=date_from,
        date_to=date_to,
        region=region,
    )

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
    region: Optional[str] = Query("vn", pattern="^(vn|global)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    articles = service.personalized_feed(
        include_portfolio=portfolio,
        include_watchlist=watchlist,
        region=region,
        limit=limit,
        offset=offset,
    )
    article_ids = [a.id for a in articles]
    symbol_map = _load_article_symbols(session, article_ids)
    total = service.count_personalized_feed(
        include_portfolio=portfolio,
        include_watchlist=watchlist,
        region=region,
    )

    return ArticleListResponse(
        items=[_article_to_schema(a, symbol_map.get(a.id, [])) for a in articles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/sources", response_model=List[NewsSourceRead])
def list_sources(session: Session = Depends(get_session)):
    rows = session.exec(
        select(NewsSource)
        .where(NewsSource.is_active == True)
        .order_by(NewsSource.name)
    ).all()
    return [
        NewsSourceRead(id=s.id, name=s.name, code=s.code, region=s.region)
        for s in rows
    ]


@router.post("/ai-summary", response_model=AiSummaryResponse)
def ai_summary(
    payload: AiSummaryRequest,
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    articles = service.list_articles(
        symbol=payload.symbol,
        source_id=payload.source_id,
        sentiment=payload.sentiment,
        min_impact=payload.min_impact,
        search=payload.search,
        tag=payload.tag,
        date_from=payload.date_from,
        date_to=payload.date_to,
        region=payload.region,
        limit=payload.limit,
    )

    rag = RagContextService(session)
    language = articles[0].language if articles else "vi"
    rag_context = rag.format_context(
        rag.build_context(
            title=articles[0].title if articles else None,
            summary=articles[0].summary if articles else None,
            include_user_facts=True,
            include_similar_articles=True,
        ),
        language=language or "vi",
    )

    local_settings = Settings()
    ai = NewsAI(
        base_url=local_settings.OLLAMA_BASE_URL,
        model=local_settings.OLLAMA_MODEL,
        timeout=local_settings.OLLAMA_TIMEOUT,
        enabled=local_settings.OLLAMA_ENABLED,
    )
    summary = ai.summarize(
        [
            {
                "title": a.title,
                "summary": a.summary,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "url": a.url,
                "tags": a.tags,
                "symbols": service.get_article_symbols(a.id),
                "impact_score": a.impact_score,
                "relevance_score": a.relevance_score,
            }
            for a in articles
        ],
        language=language or "vi",
        rag_context=rag_context if rag_context else None,
    )

    return AiSummaryResponse(
        summary=summary,
        article_count=len(articles),
        used_ollama=local_settings.AI_PROVIDER == "ollama",
        personalized=bool(rag_context),
    )


@router.get("/trending/now", response_model=TrendingResponse)
def trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    region: Optional[str] = Query("vn", pattern="^(vn|global)$"),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    data = service.trending(hours=hours, limit=limit, region=region)
    return TrendingResponse(
        symbols=[TrendingSymbol(symbol=item["symbol"], mentions=item["mentions"]) for item in data["symbols"]],
        sentiment=data["sentiment"],
    )


@router.get("/brief/daily", response_model=DailyBriefResponse)
def daily_brief(
    hours: int = Query(24, ge=1, le=168),
    scope: Optional[str] = Query(None, pattern="^(vn|global)$"),
    session: Session = Depends(get_session),
):
    service = NewsFeedService(session)
    data = service.daily_brief(hours=hours, scope=scope)
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


def _run_refresh_job(job_id: str, source: Optional[str], region: Optional[str] = None) -> None:
    """Background worker that crawls sources and updates the job state."""
    from database import engine

    job = RefreshTracker.get(job_id)
    if job is None:
        return

    try:
        with Session(engine) as session:
            crawler = NewsCrawlerService(session)
            if region:
                results = crawler.crawl_region(region, progress=job)
            else:
                results = crawler.refresh(source_code=source, progress=job)
            alerts_service = AlertService(session)
            alerts_count = alerts_service.generate_alerts(hours=1) if region != "global" else 0
            job.update(
                status="completed",
                results=results,
                alerts_generated=alerts_count,
                message="Hoàn tất",
            )
    except Exception as exc:
        job.update(status="error", message=str(exc))
        job.add_error(str(exc))


async def _refresh_stream(job_id: str) -> AsyncGenerator[str, None]:
    """SSE generator that yields progress events until the job finishes."""
    job = RefreshTracker.get(job_id)
    if job is None:
        payload = json.dumps({"message": "Không tìm thấy tiến trình"})
        yield f"event: error\ndata: {payload}\n\n"
        return

    last_state = None
    while True:
        current = job.to_dict()
        if current != last_state:
            yield f"event: progress\ndata: {json.dumps(current)}\n\n"
            last_state = current
        if current["status"] in ("completed", "error", "timeout"):
            yield f"event: {current['status']}\ndata: {json.dumps(current)}\n\n"
            break
        await asyncio.sleep(0.5)


@router.post("/refresh")
def refresh_news_start(
    source: Optional[str] = Query(None),
    region: Optional[str] = Query(None, pattern="^(vn|global)$"),
):
    """Start a refresh job in the background and return its id."""
    job = RefreshTracker.create(source_code=source or region)
    thread = threading.Thread(
        target=_run_refresh_job, args=(job.id, source, region), daemon=True
    )
    thread.start()
    return {"job_id": job.id}


@router.get("/refresh/{job_id}")
def refresh_news_status(job_id: str):
    """Poll the current status of a refresh job."""
    job = RefreshTracker.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiến trình")
    return job.to_dict()


@router.get("/refresh/{job_id}/stream")
def refresh_news_stream(job_id: str):
    """Stream refresh progress via SSE (pure HTTP)."""
    return StreamingResponse(
        _refresh_stream(job_id),
        media_type="text/event-stream",
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(article_id: int, session: Session = Depends(get_session)):
    service = NewsFeedService(session)
    article = service.get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    symbols = service.get_article_symbols(article_id)
    return _article_to_schema(article, symbols)
