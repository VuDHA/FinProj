import datetime
from typing import Dict, List

import feedparser
import requests

from services.news.sources.base import NewsSourceAdapter


class BloombergNewsSource(NewsSourceAdapter):
    code = "bloomberg"
    name = "Bloomberg Markets"
    language = "en"
    source_type = "rss"
    feed_url = "https://feeds.bloomberg.com/markets/news.rss"
    base_url = "https://www.bloomberg.com"
    region = "global"

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def fetch(self) -> List[Dict]:
        try:
            response = requests.get(
                self.feed_url,
                timeout=30,
                headers=self._headers,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[news:{self.code}] fetch failed: {e}")
            return []

        feed = feedparser.parse(response.content)
        articles = []
        for entry in feed.entries:
            published_at = None
            if entry.get("published_parsed"):
                published_at = datetime.datetime(*entry.published_parsed[:6])

            raw = {
                "url": entry.get("link"),
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "content_text": entry.get("summary"),
                "content_html": None,
                "author": entry.get("author"),
                "category": entry.get("category"),
                "tags": None,
                "published_at": published_at,
            }
            articles.append(self.normalize(raw))

        return articles
