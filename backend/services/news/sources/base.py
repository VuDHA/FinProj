import datetime
import re
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
        published_at = raw.get("published_at")
        if not published_at:
            published_at = self._resolve_published_at(
                raw.get("published_at_text"),
                raw.get("url"),
            )
        return {
            "url": raw.get("url"),
            "title": raw.get("title"),
            "summary": raw.get("summary"),
            "content_text": raw.get("content_text") or raw.get("summary"),
            "content_html": raw.get("content_html"),
            "author": raw.get("author"),
            "category": raw.get("category"),
            "tags": raw.get("tags"),
            "published_at": published_at,
            "language": self.language,
            "region": self.region,
        }

    @staticmethod
    def _resolve_published_at(
        text: Optional[str] = None,
        url: Optional[str] = None,
    ) -> datetime.datetime:
        """Return a best-effort published datetime.

        Priority:
        1. Parse the provided text.
        2. Try to infer a date from the URL path.
        3. Fall back to the current UTC time so the field is never null.
        """
        if text:
            parsed = NewsSourceAdapter._parse_time(text)
            if parsed:
                return parsed
        if url:
            parsed = NewsSourceAdapter._parse_time_from_url(url)
            if parsed:
                return parsed
        return datetime.datetime.utcnow()

    @staticmethod
    def _parse_time(text: str) -> Optional[datetime.datetime]:
        """Parse a wide variety of Vietnamese/English datetime strings."""
        if not text:
            return None
        text = text.strip().lower()
        if not text:
            return None

        now = datetime.datetime.utcnow()

        # Relative time like "2 giờ trước", "15 phút trước", "1h trước"
        match = re.search(r"(\d+)\s*(giờ|h|phút|p)\s*trước", text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            delta = (
                datetime.timedelta(hours=amount)
                if unit in ("giờ", "h")
                else datetime.timedelta(minutes=amount)
            )
            return now - delta

        # "Hôm nay" / "Hôm qua" with an optional time
        if "hôm nay" in text:
            time_match = re.search(r"(\d{1,2}):(\d{2})", text)
            if time_match:
                return now.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0,
                    microsecond=0,
                )
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if "hôm qua" in text:
            time_match = re.search(r"(\d{1,2}):(\d{2})", text)
            yesterday = now - datetime.timedelta(days=1)
            if time_match:
                return yesterday.replace(
                    hour=int(time_match.group(1)),
                    minute=int(time_match.group(2)),
                    second=0,
                    microsecond=0,
                )
            return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

        # "Vừa xong", "mới đây", "mới"
        if any(k in text for k in ("vừa xong", "mới đây", "vừa đăng", "mới")):
            return now

        # Strip Vietnamese day-of-week prefixes, "ngày", "lúc", and extra commas
        cleaned = re.sub(
            r"(chủ nhật|thứ [\w\s]+?)[,\s]+",
            "",
            text,
            flags=re.UNICODE,
        )
        cleaned = re.sub(r"\b(ngày|lúc|vào)\s+", "", cleaned)
        cleaned = re.sub(r"\s+\|\s+", " ", cleaned)
        cleaned = cleaned.strip()

        formats = (
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%H:%M %d/%m/%Y",
            "%d/%m %H:%M",
            "%d/%m/%Y",
            "%d/%m",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%H:%M %d-%m-%Y",
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y",
            "%Y-%m-%d",
        )
        for fmt in formats:
            try:
                parsed = datetime.datetime.strptime(cleaned, fmt)
                if parsed.year == 1900:
                    parsed = parsed.replace(year=now.year)
                return parsed
            except ValueError:
                continue

        # Try to grab a date from looser strings like "11:20 | 04/07/2025"
        loose_match = re.search(
            r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s+(\d{1,2}:\d{2})",
            cleaned,
        )
        if loose_match:
            date_part = loose_match.group(1)
            time_part = loose_match.group(2)
            for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                try:
                    parsed = datetime.datetime.strptime(date_part, fmt)
                    hour, minute = map(int, time_part.split(":"))
                    return parsed.replace(hour=hour, minute=minute, second=0)
                except ValueError:
                    continue

        return None

    @staticmethod
    def _parse_time_from_url(url: str) -> Optional[datetime.datetime]:
        """Try to extract a date from common URL patterns, e.g. /2025/07/04/."""
        if not url:
            return None
        for pattern in (
            r"/(\d{4})/(\d{2})/(\d{2})/",
            r"/(\d{4})-(\d{2})-(\d{2})/",
            r"/(\d{4})(\d{2})(\d{2})/",
        ):
            match = re.search(pattern, url)
            if match:
                try:
                    year, month, day = map(int, match.groups())
                    return datetime.datetime(year, month, day, 0, 0, 0)
                except ValueError:
                    continue

        # Some sites only put year/month in the path (e.g. VietStock /2026/07/).
        # In that case fall back to the first day of the month.
        for pattern in (
            r"/(\d{4})/(\d{2})/",
            r"/(\d{4})-(\d{2})/",
        ):
            match = re.search(pattern, url)
            if match:
                try:
                    year, month = map(int, match.groups())
                    return datetime.datetime(year, month, 1, 0, 0, 0)
                except ValueError:
                    continue
        return None


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
