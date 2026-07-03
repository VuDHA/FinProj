import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class NewsSourceAdapter(ABC):
    """Abstract adapter for a news source."""

    code: str
    name: str
    language: str = "en"
    source_type: str = "rss"  # rss, sitemap, html
    feed_url: Optional[str] = None
    base_url: Optional[str] = None
    is_active: bool = True
    region: str = "vn"  # vn, global

    @abstractmethod
    def fetch(self) -> List[Dict]:
        """
        Fetch raw articles from the source and return a list of normalized
        article dictionaries with at least:
        {
            "url": str,
            "title": str,
            "summary": str | None,
            "content_text": str | None,
            "content_html": str | None,
            "author": str | None,
            "category": str | None,
            "tags": str | None,
            "published_at": datetime.datetime | None,
        }
        """
        pass

    def normalize(self, raw: Dict) -> Dict:
        """Default normalization. Subclasses may override."""
        return {
            "url": raw.get("url"),
            "title": raw.get("title"),
            "summary": raw.get("summary"),
            "content_text": raw.get("content_text") or raw.get("summary"),
            "content_html": raw.get("content_html"),
            "author": raw.get("author"),
            "category": raw.get("category"),
            "tags": raw.get("tags"),
            "published_at": raw.get("published_at"),
            "language": self.language,
            "region": self.region,
        }


class NewsSourceRegistry:
    """Registry of available news source adapters."""

    def __init__(self):
        self._sources: Dict[str, NewsSourceAdapter] = {}

    def register(self, source: NewsSourceAdapter):
        self._sources[source.code] = source

    def get(self, code: str) -> Optional[NewsSourceAdapter]:
        return self._sources.get(code)

    def all(self) -> List[NewsSourceAdapter]:
        return [s for s in self._sources.values() if s.is_active]

    def for_region(self, region: str) -> List[NewsSourceAdapter]:
        return [s for s in self._sources.values() if s.is_active and s.region == region]

    def codes(self) -> List[str]:
        return [s.code for s in self.all()]
