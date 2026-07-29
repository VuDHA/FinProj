import datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

from models import NewsArticle, NewsSource, NewsSymbol
from services.embedding_store import EmbeddingStore
from services.news.dictionaries import get_known_symbols
from services.news.processor import NewsProcessor
from services.news.sources import registry


class NewsCrawlerService:
    """Orchestrates crawling, processing, and storing news articles."""

    def __init__(self, session: Session):
        self.session = session
        self.processor = NewsProcessor(known_symbols=get_known_symbols(), session=session)
        self.embedding_store = EmbeddingStore()
        self._disable_orphan_sources()

    def _disable_orphan_sources(self):
        """Mark sources that are no longer registered as inactive."""
        registered = registry.codes()
        orphans = self.session.exec(
            select(NewsSource).where(NewsSource.is_active == True).where(NewsSource.code.notin_(registered))
        ).all()
        for source in orphans:
            source.is_active = False
            self.session.add(source)
        if orphans:
            self.session.commit()

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
                region=adapter.region,
            )
            self.session.add(source)
            self.session.commit()
            self.session.refresh(source)
        else:
            source.region = adapter.region
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

        if not data.get("is_standout"):
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
            relevance_score=data.get("relevance_score"),
            is_standout=data.get("is_standout", False),
            language=data.get("language"),
            region=data.get("region", source.region),
        )
        try:
            self.session.add(article)
            self.session.flush()
            self.session.refresh(article)
        except IntegrityError:
            # Article already exists (duplicate URL), skip it
            self.session.rollback()
            return None

        for symbol in data.get("symbols", []):
            link = NewsSymbol(article_id=article.id, symbol=symbol)
            self.session.add(link)

        return article

    def _embed_batch(self, articles: List[NewsArticle]) -> None:
        """Generate embeddings for a list of saved articles in one API call."""
        items = []
        for article in articles:
            text = " ".join(filter(None, [article.title, article.summary])).strip()
            if text:
                items.append((article.id, text))
        if items:
            self.embedding_store.create_embeddings_batch(items)

    def crawl_source(self, code: str, progress: Optional[Any] = None) -> int:
        """Crawl a single source by code. Returns number of new articles stored."""
        adapter = registry.get(code)
        if adapter is None:
            print(f"[news:crawler] unknown source: {code}")
            if progress is not None:
                progress.add_error(f"Không rõ nguồn: {code}")
            return 0

        source = self._get_or_create_source(adapter)
        if not source.is_active:
            return 0

        if progress is not None:
            progress.update(current_source=code, message=f"Đang lấy tin từ {code}...")

        try:
            raw_articles = adapter.fetch()
        except Exception as e:
            print(f"[news:crawler] error fetching {code}: {e}")
            if progress is not None:
                progress.add_error(f"{code}: {e}")
            return 0

        # Skip articles that are already stored so we don't re-score/analyze them.
        new_articles = [
            a
            for a in raw_articles
            if a.get("url") and a.get("title") and not self._exists(a["url"], a["title"])
        ]
        skipped = len(raw_articles) - len(new_articles)
        if skipped:
            print(f"[news:crawler] {code}: skipped {skipped} already-stored articles")

        if progress is not None:
            progress.update(
                processed=progress.processed + len(raw_articles),
                message=f"Đang xử lý {len(new_articles)} tin mới từ {code}...",
            )

        processed = self.processor.process_many(new_articles)
        saved_articles: List[NewsArticle] = []
        for article in processed:
            saved = self._save_article(source, article)
            if saved:
                saved_articles.append(saved)

        # Commit articles/symbol links first so the embedding writer does not
        # compete with the open session transaction for the SQLite lock.
        source.last_crawled_at = datetime.datetime.utcnow()
        self.session.commit()

        # Generate embeddings for all saved articles in one batched API call.
        self._embed_batch(saved_articles)

        new_count = len(saved_articles)
        print(f"[news:crawler] {code}: {new_count} new articles out of {len(processed)}")

        if progress is not None:
            progress.update(
                new_articles=progress.new_articles + new_count,
                results={**progress.results, code: new_count},
                message=f"{code}: +{new_count} tin mới",
            )
        return new_count

    def crawl_all(self, progress: Optional[Any] = None) -> Dict[str, int]:
        """Crawl all active sources. Returns mapping source_code -> new_count."""
        adapters = registry.all()
        if progress is not None:
            progress.update(total_sources=len(adapters), current_source_index=0)
        results = {}
        for index, adapter in enumerate(adapters, start=1):
            if progress is not None:
                progress.update(current_source_index=index, current_source=adapter.code)
            results[adapter.code] = self.crawl_source(adapter.code, progress=progress)
        return results

    def crawl_region(self, region: str, progress: Optional[Any] = None) -> Dict[str, int]:
        """Crawl all active sources for a specific region."""
        adapters = registry.for_region(region)
        if progress is not None:
            progress.update(total_sources=len(adapters), current_source_index=0)
        results = {}
        for index, adapter in enumerate(adapters, start=1):
            if progress is not None:
                progress.update(current_source_index=index, current_source=adapter.code)
            results[adapter.code] = self.crawl_source(adapter.code, progress=progress)
        return results

    def refresh(self, source_code: Optional[str] = None, progress: Optional[Any] = None) -> Dict[str, int]:
        """Public entry point for manual or scheduled refresh."""
        if source_code:
            if progress is not None:
                progress.update(total_sources=1, current_source_index=1, current_source=source_code)
            return {source_code: self.crawl_source(source_code, progress=progress)}
        return self.crawl_all(progress=progress)
