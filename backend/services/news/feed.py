import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models import Asset, NewsAlert, NewsArticle, NewsSymbol, Watchlist
from services.news.dictionaries import sentiment_label


class NewsFeedService:
    """Build personalized feeds, trending lists, and daily briefs from stored news."""

    def __init__(self, session: Session):
        self.session = session

    def _base_article_query(self):
        return select(NewsArticle).where(NewsArticle.is_active == True)

    def _apply_article_filters(
        self,
        query,
        symbol: Optional[str] = None,
        source_id: Optional[int] = None,
        sentiment: Optional[str] = None,
        min_impact: Optional[float] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        tag: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Apply shared filtering logic to a news query (list or count)."""
        if region:
            query = query.where(NewsArticle.region == region)

        if symbol:
            query = query.join(NewsSymbol).where(NewsSymbol.symbol == symbol.upper())

        if source_id:
            query = query.where(NewsArticle.source_id == source_id)

        if sentiment:
            if sentiment == "positive":
                query = query.where(NewsArticle.sentiment_score > 0.15)
            elif sentiment == "negative":
                query = query.where(NewsArticle.sentiment_score < -0.15)
            elif sentiment == "neutral":
                query = query.where(
                    (NewsArticle.sentiment_score >= -0.15)
                    & (NewsArticle.sentiment_score <= 0.15)
                )

        if min_impact is not None:
            query = query.where(NewsArticle.impact_score >= min_impact)

        if search:
            pattern = f"%{search}%"
            query = query.where(
                (NewsArticle.title.ilike(pattern))
                | (NewsArticle.summary.ilike(pattern))
                | (NewsArticle.content_text.ilike(pattern))
            )

        if date_from:
            query = query.where(NewsArticle.published_at >= datetime.datetime.combine(date_from, datetime.time.min))

        if date_to:
            query = query.where(NewsArticle.published_at <= datetime.datetime.combine(date_to, datetime.time.max))

        if tag:
            pattern = f"%{tag}%"
            query = query.where(NewsArticle.tags.ilike(pattern))

        return query

    def list_articles(
        self,
        symbol: Optional[str] = None,
        source_id: Optional[int] = None,
        sentiment: Optional[str] = None,
        min_impact: Optional[float] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        tag: Optional[str] = None,
        region: Optional[str] = "vn",
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewsArticle]:
        query = self._apply_article_filters(
            self._base_article_query(),
            symbol=symbol,
            source_id=source_id,
            sentiment=sentiment,
            min_impact=min_impact,
            search=search,
            date_from=date_from,
            date_to=date_to,
            tag=tag,
            region=region,
        )
        query = query.order_by(func.coalesce(NewsArticle.published_at, NewsArticle.fetched_at).desc()).offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def count_articles(
        self,
        symbol: Optional[str] = None,
        source_id: Optional[int] = None,
        sentiment: Optional[str] = None,
        min_impact: Optional[float] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        tag: Optional[str] = None,
        region: Optional[str] = "vn",
    ) -> int:
        query = self._apply_article_filters(
            select(func.count(func.distinct(NewsArticle.id))).where(NewsArticle.is_active == True),
            symbol=symbol,
            source_id=source_id,
            sentiment=sentiment,
            min_impact=min_impact,
            search=search,
            date_from=date_from,
            date_to=date_to,
            tag=tag,
            region=region,
        )
        return self.session.exec(query).one()

    def get_article(self, article_id: int) -> Optional[NewsArticle]:
        return self.session.get(NewsArticle, article_id)

    def get_article_symbols(self, article_id: int) -> List[str]:
        symbols = self.session.exec(
            select(NewsSymbol.symbol).where(NewsSymbol.article_id == article_id)
        ).all()
        return list(symbols)

    def _personalized_symbols(
        self, include_portfolio: bool = True, include_watchlist: bool = True
    ) -> set[str]:
        symbols: set[str] = set()

        if include_portfolio:
            assets = self.session.exec(select(Asset.symbol).where(Asset.is_active == True)).all()
            symbols.update(a.upper() for a in assets if a)

        if include_watchlist:
            watchlist = self.session.exec(select(Watchlist.symbol)).all()
            symbols.update(w.upper() for w in watchlist if w)

        return symbols

    def personalized_feed(
        self,
        include_portfolio: bool = True,
        include_watchlist: bool = True,
        limit: int = 20,
        offset: int = 0,
        region: Optional[str] = "vn",
    ) -> List[NewsArticle]:
        symbols = self._personalized_symbols(include_portfolio, include_watchlist)

        if not symbols:
            return []

        query = (
            select(NewsArticle)
            .join(NewsSymbol)
            .where(NewsSymbol.symbol.in_(list(symbols)))
            .where(NewsArticle.is_active == True)
        )
        if region:
            query = query.where(NewsArticle.region == region)
        query = query.order_by(func.coalesce(NewsArticle.published_at, NewsArticle.fetched_at).desc()).offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def count_personalized_feed(
        self,
        include_portfolio: bool = True,
        include_watchlist: bool = True,
        region: Optional[str] = "vn",
    ) -> int:
        symbols = self._personalized_symbols(include_portfolio, include_watchlist)

        if not symbols:
            return 0

        query = (
            select(func.count(func.distinct(NewsArticle.id)))
            .join(NewsSymbol)
            .where(NewsSymbol.symbol.in_(list(symbols)))
            .where(NewsArticle.is_active == True)
        )
        if region:
            query = query.where(NewsArticle.region == region)
        return self.session.exec(query).one()

    def trending(
        self,
        hours: int = 24,
        limit: int = 10,
        region: Optional[str] = "vn",
    ) -> Dict[str, List[Dict]]:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

        # Most mentioned symbols
        symbol_counts = self.session.exec(
            select(NewsSymbol.symbol, func.count(NewsSymbol.id).label("count"))
            .join(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .where(NewsArticle.region == region)
            .group_by(NewsSymbol.symbol)
            .order_by(func.count(NewsSymbol.id).desc())
            .limit(limit)
        ).all()

        # Most active articles by impact
        hot_articles = self.session.exec(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .where(NewsArticle.region == region)
            .order_by(NewsArticle.impact_score.desc(), NewsArticle.published_at.desc())
            .limit(limit)
        ).all()

        # Sentiment distribution
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        all_recent = self.session.exec(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .where(NewsArticle.region == region)
        ).all()
        for article in all_recent:
            sentiment_counts[sentiment_label(article.sentiment_score)] += 1

        return {
            "symbols": [{"symbol": s, "mentions": c} for s, c in symbol_counts],
            "articles": hot_articles,
            "sentiment": sentiment_counts,
        }

    def daily_brief(self, hours: int = 24, scope: Optional[str] = None) -> Dict[str, any]:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        region = scope if scope in ("vn", "global") else "vn"
        query = (
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .where(NewsArticle.region == region)
        )
        articles = self.session.exec(
            query.order_by(NewsArticle.impact_score.desc(), NewsArticle.published_at.desc()).limit(10)
        ).all()

        return {
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "period_hours": hours,
            "total_articles": len(articles),
            "top_articles": articles,
            "key_symbols": self._top_symbols_for_articles([a.id for a in articles]),
        }

    def _top_symbols_for_articles(self, article_ids: List[int], limit: int = 10) -> List[Dict]:
        if not article_ids:
            return []
        rows = self.session.exec(
            select(NewsSymbol.symbol, func.count(NewsSymbol.id).label("count"))
            .where(NewsSymbol.article_id.in_(article_ids))
            .group_by(NewsSymbol.symbol)
            .order_by(func.count(NewsSymbol.id).desc())
            .limit(limit)
        ).all()
        return [{"symbol": s, "mentions": c} for s, c in rows]
