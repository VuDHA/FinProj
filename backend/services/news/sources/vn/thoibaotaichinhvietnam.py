import json
import re
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from services.news.sources.base import NewsSourceAdapter


class ThoiBaoTaiChinhVietNamNewsSource(NewsSourceAdapter):
    code = "tbtcvn"
    name = "Thời Báo Tài Chính Việt Nam"
    language = "vi"
    source_type = "html"
    base_url = "https://thoibaotaichinhvietnam.vn"
    region = "vn"

    categories = [
        "chung-khoan",
        "tai-chinh",
        "ngan-hang-bao-hiem",
        "dau-tu",
        "doanh-nghiep",
        "thi-truong",
    ]

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    }

    def fetch(self) -> List[Dict]:
        articles = []
        seen = set()
        for category in self.categories:
            page_items = self._fetch_category(category)
            print(f"[news:{self.code}] {category}: {len(page_items)} items")

            for item in page_items:
                if item["url"] in seen:
                    continue
                seen.add(item["url"])

                # Use the date from the listing page if available; skip the
                # per-article detail fetch which makes the crawl extremely slow
                # (6 categories × dozens of articles × 30s timeout each).
                published_at_text = item.get("published_at_text")

                raw = {
                    "url": item["url"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "content_text": item["summary"],
                    "content_html": None,
                    "author": None,
                    "category": category,
                    "tags": None,
                    "published_at": None,
                    "published_at_text": published_at_text,
                }
                articles.append(self.normalize(raw))

        return articles

    def _fetch_category(self, category: str) -> List[Dict]:
        paths = [
            f"/{category}",
            f"/{category}/",
        ]
        for path in paths:
            url = urljoin(self.base_url, path)
            try:
                response = requests.get(url, timeout=30, headers=self._headers)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"[news:{self.code}] fetch failed for {url}: {e}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            items = self._extract_items(soup)
            if items:
                return items
        return []

    def _extract_items(self, soup: BeautifulSoup) -> List[Dict]:
        items = []
        seen = set()

        # The site lists articles as heading links followed by a short paragraph
        # or inside article/div containers. Try several patterns.
        containers = (
            soup.find_all("article")
            or soup.find_all("div", class_=re.compile("item|news|post|article"))
            or soup.find_all("li", class_=re.compile("item|news"))
        )

        for container in containers:
            link = container.find("a", href=True)
            if not link:
                continue

            href = urljoin(self.base_url, link.get("href", ""))
            if not href.startswith(self.base_url):
                continue

            # Skip non-article pages (categories, tags, media, etc.)
            if not href.endswith(".html"):
                continue

            title = self._clean_text(link.get("title") or link.get_text())
            if not title or href in seen:
                continue
            seen.add(href)

            summary = ""
            p = container.find("p")
            if p:
                summary = self._clean_text(p.get_text())
            else:
                sapo = container.find(class_=re.compile("sapo|summary|des|lead"))
                if sapo:
                    summary = self._clean_text(sapo.get_text())

            published_at_text = None
            time_tag = container.find("time")
            if time_tag:
                published_at_text = self._clean_text(
                    time_tag.get_text() or time_tag.get("datetime", "")
                )
            if not published_at_text:
                time_span = container.find(class_=re.compile("time|date|hour|meta"))
                if time_span:
                    published_at_text = self._clean_text(time_span.get_text())

            items.append(
                {
                    "url": href,
                    "title": title,
                    "summary": summary,
                    "published_at": None,
                    "published_at_text": published_at_text,
                }
            )

        # Fallback: if no containers matched, scrape all heading links
        if not items:
            for tag in soup.find_all(["h2", "h3", "h4"]):
                link = tag.find("a", href=True)
                if not link:
                    continue
                href = urljoin(self.base_url, link.get("href", ""))
                if not href.startswith(self.base_url) or not href.endswith(".html"):
                    continue
                if href in seen:
                    continue
                seen.add(href)
                title = self._clean_text(link.get_text())
                if not title:
                    continue
                items.append(
                    {
                        "url": href,
                        "title": title,
                        "summary": "",
                        "published_at": None,
                        "published_at_text": None,
                    }
                )

        return items

    def _fetch_detail_date(self, url: str) -> str | None:
        """Fetch the article detail page and extract the published date text.

        The site exposes the date in schema.org JSON-LD, in a .calendar span, or
        in a .format_date span. Any non-empty text is returned so the shared
        _parse_time helper can normalize it.
        """
        try:
            response = requests.get(url, timeout=30, headers=self._headers)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[news:{self.code}] detail fetch failed for {url}: {e}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Schema.org JSON-LD datePublished
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.get_text() or "")
            except Exception:
                continue
            if isinstance(data, dict) and data.get("datePublished"):
                return str(data["datePublished"])
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("datePublished"):
                        return str(item["datePublished"])

        # 2. Visible date spans
        for cls in ("calendar", "format_date", "post-date", "published"):
            span = soup.find(attrs={"class": cls})
            if span:
                text = self._clean_text(span.get_text())
                if text:
                    return text

        # 3. Any <time> tag with datetime
        time_tag = soup.find("time")
        if time_tag:
            return time_tag.get("datetime") or self._clean_text(time_tag.get_text())

        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())
