import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from models import Asset, NewsAlert, NewsArticle, NewsSymbol, Watchlist
from services.news.dictionaries import sentiment_label


class AlertService:
    """Generate and manage user alerts from news articles."""

    def __init__(self, session: Session):
        self.session = session

    def _monitored_symbols(self) -> set[str]:
        symbols = set()
        assets = self.session.exec(select(Asset.symbol).where(Asset.is_active == True)).all()
        symbols.update(a.upper() for a in assets if a)
        watchlist = self.session.exec(select(Watchlist.symbol)).all()
        symbols.update(w.upper() for w in watchlist if w)
        return symbols

    def generate_alerts(self, hours: int = 1) -> int:
        """
        Scan recent articles and create alerts for monitored symbols.
        Returns number of alerts created.
        """
        since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        monitored = self._monitored_symbols()
        if not monitored:
            return 0

        new_alerts = 0
        # Find recent articles mentioning monitored symbols
        articles = self.session.exec(
            select(NewsArticle)
            .join(NewsSymbol)
            .where(NewsSymbol.symbol.in_(list(monitored)))
            .where(NewsArticle.published_at >= since)
            .where(NewsArticle.is_active == True)
            .order_by(NewsArticle.published_at.desc())
        ).all()

        for article in articles:
            symbols = self.session.exec(
                select(NewsSymbol.symbol).where(NewsSymbol.article_id == article.id)
            ).all()
            for symbol in symbols:
                if symbol.upper() not in monitored:
                    continue

                # Avoid duplicate alerts for the same symbol+article
                existing = self.session.exec(
                    select(NewsAlert).where(
                        (NewsAlert.article_id == article.id)
                        & (NewsAlert.symbol == symbol.upper())
                    )
                ).first()
                if existing:
                    continue

                alert_type = "symbol"
                message = f"Tin mới về {symbol}: {article.title}"
                if article.impact_score and article.impact_score >= 0.6:
                    alert_type = "breaking"
                    message = f"Tin quan trọng về {symbol}: {article.title}"
                elif sentiment_label(article.sentiment_score) == "negative":
                    alert_type = "sentiment"
                    message = f"Tin tiêu cực về {symbol}: {article.title}"

                alert = NewsAlert(
                    alert_type=alert_type,
                    symbol=symbol.upper(),
                    article_id=article.id,
                    title=article.title[:200],
                    message=message[:500],
                )
                self.session.add(alert)
                new_alerts += 1

        # Volume spike detection: any symbol with many recent articles
        since_volume = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        volume_rows = self.session.exec(
            select(NewsSymbol.symbol, func.count(NewsSymbol.id).label("count"))
            .join(NewsArticle)
            .where(NewsArticle.published_at >= since_volume)
            .where(NewsArticle.is_active == True)
            .group_by(NewsSymbol.symbol)
            .having(func.count(NewsSymbol.id) >= 3)
        ).all()

        for symbol, count in volume_rows:
            if symbol.upper() not in monitored:
                continue
            # One volume alert per symbol per 4h window
            existing = self.session.exec(
                select(NewsAlert).where(
                    (NewsAlert.symbol == symbol.upper())
                    & (NewsAlert.alert_type == "volume")
                    & (NewsAlert.created_at >= since_volume)
                )
            ).first()
            if existing:
                continue
            # Pick the most recent article for this symbol
            article = self.session.exec(
                select(NewsArticle)
                .join(NewsSymbol)
                .where(NewsSymbol.symbol == symbol.upper())
                .where(NewsArticle.is_active == True)
                .order_by(NewsArticle.published_at.desc())
                .limit(1)
            ).first()
            if article:
                alert = NewsAlert(
                    alert_type="volume",
                    symbol=symbol.upper(),
                    article_id=article.id,
                    title=f"Nhiều tin về {symbol}",
                    message=f"Có {count} tin đề cập đến {symbol} trong 4 giờ qua.",
                )
                self.session.add(alert)
                new_alerts += 1

        self.session.commit()
        return new_alerts

    def list_alerts(self, unread_only: bool = False, limit: int = 50) -> List[NewsAlert]:
        query = select(NewsAlert).order_by(NewsAlert.created_at.desc())
        if unread_only:
            query = query.where(NewsAlert.is_read == False)
        query = query.limit(limit)
        return list(self.session.exec(query).all())

    def mark_read(self, alert_id: int) -> Optional[NewsAlert]:
        alert = self.session.get(NewsAlert, alert_id)
        if alert:
            alert.is_read = True
            self.session.add(alert)
            self.session.commit()
            self.session.refresh(alert)
        return alert

    def unread_count(self) -> int:
        return self.session.exec(
            select(func.count(NewsAlert.id)).where(NewsAlert.is_read == False)
        ).one()
