import datetime
from typing import Dict, List, Optional

import feedparser
import requests

from services.news.sources.base import NewsSourceAdapter


class YahooFinanceNewsSource(NewsSourceAdapter):
    code = "yahoo_finance"
    name = "Yahoo Finance"
    language = "en"
    source_type = "rss"
    feed_url = "https://finance.yahoo.com/news/rssindex"
    base_url = "https://finance.yahoo.com"

    def fetch(self) -> List[Dict]:
        try:
            response = requests.get(
                self.feed_url,
                timeout=30,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
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
                "category": None,
                "tags": None,
                "published_at": published_at,
            }
            articles.append(self.normalize(raw))

        return articles
