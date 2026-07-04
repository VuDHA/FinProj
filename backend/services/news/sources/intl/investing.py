import datetime
import re
from typing import Dict, List

import feedparser
import requests

from services.news.sources.base import NewsSourceAdapter


class InvestingNewsSource(NewsSourceAdapter):
    code = "investing"
    name = "Investing.com"
    language = "en"
    source_type = "rss"
    feed_url = "https://www.investing.com/rss/investing_news.rss"
    base_url = "https://www.investing.com"
    region = "global"

    # Only keep finance-related categories from the all-news feed.
    _allowed_categories = {
        "stock-market-news",
        "economy-news",
        "commodities-news",
        "cryptocurrency-news",
        "forex-news",
        "bonds-news",
        "etfs-news",
    }

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
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
            url = entry.get("link", "")
            if not self._is_finance_url(url):
                continue

            published_at = None
            if entry.get("published_parsed"):
                published_at = datetime.datetime(*entry.published_parsed[:6])

            # The investing.com feeds do not include summaries, so use title as
            # the summary when no description is available.
            title = entry.get("title", "")
            summary = entry.get("summary") or title
            if summary == title:
                summary = ""

            raw = {
                "url": url,
                "title": title,
                "summary": summary,
                "content_text": summary,
                "content_html": None,
                "author": entry.get("author"),
                "category": self._extract_category(url),
                "tags": None,
                "published_at": published_at,
            }
            articles.append(self.normalize(raw))

        return articles

    def _is_finance_url(self, url: str) -> bool:
        if not url:
            return False
        if not url.startswith(self.base_url):
            return False
        match = re.search(r"/news/([^/]+)/", url)
        if not match:
            # Keep analysis/opinion articles too if they look market-related
            return "/analysis/" in url
        return match.group(1) in self._allowed_categories

    def _extract_category(self, url: str) -> str | None:
        match = re.search(r"/news/([^/]+)/", url)
        if match:
            return match.group(1)
        if "/analysis/" in url:
            return "analysis"
        return None
