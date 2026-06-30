import datetime
import hashlib
from typing import Dict, List, Optional

from sqlmodel import Session, select

from models import NewsArticle, NewsSource, NewsSymbol
from services.news.dictionaries import get_known_symbols
from services.news.processor import NewsProcessor
from services.news.sources import registry


class NewsCrawlerService:
    """Orchestrates crawling, processing, and storing news articles."""

    def __init__(self, session: Session):
        self.session = session
        self.processor = NewsProcessor(known_symbols=get_known_symbols())

    def _get_or_create_source(self, adapter) -> NewsSource:
        source = self.session.exec(
            select(NewsSource).where(NewsSource.code == adapter.code)
        ).first()
        if source is None:
            source = NewsSource(
                code=adapter.code,
                name=adapter.name,
                base_url=adapter.base_url,
                source_type=adapter.source_type,
                feed_url=getattr(adapter, "feed_url", None),
                language=adapter.language,
            )
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        return source

    def _article_hash(self, url: str, title: str) -> str:
        """Create a stable deduplication hash."""
        key = f"{url}|{title.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]

    def _exists(self, url: str, title: str) -> bool:
        return (
            self.session.exec(
                select(NewsArticle).where(
                    (NewsArticle.url == url) | (NewsArticle.title == title)
                )
            ).first()
            is not None
        )

    def _save_article(self, source: NewsSource, data: Dict) -> Optional[NewsArticle]:
        url = data.get("url")
        title = data.get("title")
        if not url or not title:
            return None

        if self._exists(url, title):
            return None

        article = NewsArticle(
            source_id=source.id,
            url=url,
            title=title,
            summary=data.get("summary"),
            content_text=data.get("content_text"),
            content_html=data.get("content_html"),
            author=data.get("author"),
            category=data.get("category"),
            tags=data.get("tags"),
            published_at=data.get("published_at"),
            fetched_at=data.get("fetched_at", datetime.datetime.utcnow()),
            sentiment_score=data.get("sentiment_score"),
            impact_score=data.get("impact_score"),
            language=data.get("language"),
        )
        self.session.add(article)
        self.session.flush()
        self.session.refresh(article)

        for symbol in data.get("symbols", []):
            link = NewsSymbol(article_id=article.id, symbol=symbol)
            self.session.add(link)

        return article

    def crawl_source(self, code: str) -> int:
        """Crawl a single source by code. Returns number of new articles stored."""
        adapter = registry.get(code)
        if adapter is None:
            print(f"[news:crawler] unknown source: {code}")
            return 0

        source = self._get_or_create_source(adapter)
        if not source.is_active:
            return 0

        try:
            raw_articles = adapter.fetch()
        except Exception as e:
            print(f"[news:crawler] error fetching {code}: {e}")
            return 0

        processed = self.processor.process_many(raw_articles)
        new_count = 0
        for article in processed:
            saved = self._save_article(source, article)
            if saved:
                new_count += 1

        source.last_crawled_at = datetime.datetime.utcnow()
        self.session.commit()
        print(f"[news:crawler] {code}: {new_count} new articles out of {len(processed)}")
        return new_count

    def crawl_all(self) -> Dict[str, int]:
        """Crawl all active sources. Returns mapping source_code -> new_count."""
        results = {}
        for adapter in registry.all():
            results[adapter.code] = self.crawl_source(adapter.code)
        return results

    def refresh(self, source_code: Optional[str] = None) -> Dict[str, int]:
        """Public entry point for manual or scheduled refresh."""
        if source_code:
            return {source_code: self.crawl_source(source_code)}
        return self.crawl_all()
