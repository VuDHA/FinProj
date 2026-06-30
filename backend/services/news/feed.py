import datetime
from typing import Dict, List, Optional

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

    def list_articles(
        self,
        symbol: Optional[str] = None,
        source_id: Optional[int] = None,
        sentiment: Optional[str] = None,
        min_impact: Optional[float] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewsArticle]:
        query = self._base_article_query()

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

        query = query.order_by(NewsArticle.published_at.desc()).offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def get_article(self, article_id: int) -> Optional[NewsArticle]:
        return self.session.get(NewsArticle, article_id)

    def get_article_symbols(self, article_id: int) -> List[str]:
        symbols = self.session.exec(
            select(NewsSymbol.symbol).where(NewsSymbol.article_id == article_id)
        ).all()
        return list(symbols)

    def personalized_feed(
        self,
        include_portfolio: bool = True,
        include_watchlist: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> List[NewsArticle]:
        symbols: set[str] = set()

        if include_portfolio:
            assets = self.session.exec(select(Asset.symbol).where(Asset.is_active == True)).all()
            symbols.update(a.upper() for a in assets if a)

        if include_watchlist:
            watchlist = self.session.exec(select(Watchlist.symbol)).all()
            symbols.update(w.upper() for w in watchlist if w)

        if not symbols:
            return []

        query = (
            select(NewsArticle)
            .join(NewsSymbol)
            .where(NewsSymbol.symbol.in_(list(symbols)))
            .where(NewsArticle.is_active == True)
            .order_by(NewsArticle.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.exec(query).all())

    def trending(
        self,
        hours: int = 24,
        limit: int = 10,
    ) -> Dict[str, List[Dict]]:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)

        # Most mentioned symbols
        symbol_counts = self.session.exec(
            select(NewsSymbol.symbol, func.count(NewsSymbol.id).label("count"))
            .join(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .group_by(NewsSymbol.symbol)
            .order_by(func.count(NewsSymbol.id).desc())
            .limit(limit)
        ).all()

        # Most active articles by impact
        hot_articles = self.session.exec(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .order_by(NewsArticle.impact_score.desc(), NewsArticle.published_at.desc())
            .limit(limit)
        ).all()

        # Sentiment distribution
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        all_recent = self.session.exec(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
        ).all()
        for article in all_recent:
            sentiment_counts[sentiment_label(article.sentiment_score)] += 1

        return {
            "symbols": [{"symbol": s, "mentions": c} for s, c in symbol_counts],
            "articles": hot_articles,
            "sentiment": sentiment_counts,
        }

    def daily_brief(self, hours: int = 24) -> Dict[str, any]:
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        articles = self.session.exec(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .order_by(NewsArticle.impact_score.desc(), NewsArticle.published_at.desc())
            .limit(10)
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
