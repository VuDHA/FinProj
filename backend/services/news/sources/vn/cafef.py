import datetime
import re
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from services.news.sources.base import NewsSourceAdapter


class CafeFNewsSource(NewsSourceAdapter):
    code = "cafef"
    name = "CafeF"
    language = "vi"
    source_type = "html"
    base_url = "https://cafef.vn"

    categories = [
        "tai-chinh-ngan-hang",
        "chung-khoan",
        "doanh-nghiep",
        "kinh-te-vi-mo",
    ]

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    def fetch(self) -> List[Dict]:
        articles = []
        for category in self.categories:
            page_items = self._fetch_category(category)
            print(f"[news:{self.code}] {category}: {len(page_items)} items")

            for item in page_items:
                raw = {
                    "url": item["url"],
                    "title": item["title"],
                    "summary": item["summary"],
                    "content_text": item["summary"],
                    "content_html": None,
                    "author": None,
                    "category": category,
                    "tags": None,
                    "published_at": item["published_at"],
                }
                articles.append(self.normalize(raw))

        return articles

    def _fetch_category(self, category: str) -> List[Dict]:
        paths = [
            f"/{category}.html",
            f"/{category}.chn",
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

        # Try multiple article container selectors common on CafeF
        containers = (
            soup.find_all("article")
            or soup.find_all("div", class_=re.compile("item|news|post"))
            or soup.find_all("li", class_=re.compile("item|news"))
        )

        for container in containers:
            link = container.find("a", href=True)
            if not link:
                continue

            href = urljoin(self.base_url, link.get("href", ""))
            # Skip non-article links (pagination, ads, etc.)
            if not href.startswith(self.base_url) or "/video/" in href or "/tag/" in href:
                continue

            title = self._clean_text(link.get("title") or link.get_text())
            if not title:
                h_tag = container.find(["h1", "h2", "h3", "h4"])
                if h_tag:
                    title = self._clean_text(h_tag.get_text())

            if not title or not href or href in seen:
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

            published_at = None
            time_tag = container.find("time")
            if time_tag:
                published_at = self._parse_time(time_tag.get_text()) or self._parse_time(time_tag.get("datetime", ""))
            if not published_at:
                time_span = container.find(class_=re.compile("time|date|hour"))
                if time_span:
                    published_at = self._parse_time(time_span.get_text())

            items.append({
                "url": href,
                "title": title,
                "summary": summary,
                "published_at": published_at,
            })

        return items

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def _parse_time(text: str) -> datetime.datetime | None:
        if not text:
            return None
        text = text.strip().lower()

        # Relative time like "2 giờ trước", "15 phút trước"
        match = re.search(r"(\d+)\s*(giờ|h|phút|p)\s*trước", text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            delta = datetime.timedelta(hours=amount) if unit in ("giờ", "h") else datetime.timedelta(minutes=amount)
            return datetime.datetime.utcnow() - delta

        # Common Vietnamese datetime formats
        for fmt in (
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%H:%M %d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%H:%M %d-%m-%Y",
        ):
            try:
                return datetime.datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None
