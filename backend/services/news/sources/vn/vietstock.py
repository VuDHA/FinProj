import re
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from services.news.sources.base import NewsSourceAdapter


class VietStockNewsSource(NewsSourceAdapter):
    code = "vietstock"
    name = "VietStock"
    language = "vi"
    source_type = "html"
    base_url = "https://vietstock.vn"
    region = "vn"

    categories = [
        "chung-khoan",
        "tai-chinh",
        "doanh-nghiep",
        "bat-dong-san",
        "kinh-te/kinh-te-dau-tu",
        "kinh-te/vi-mo",
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
            f"/{category}.htm",
            f"/{category}.html",
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

        # VietStock lists articles inside h4 or h2 headings with a following <p>
        # summary. Try several common container patterns.
        for tag in soup.find_all(["h2", "h3", "h4"]):
            link = tag.find("a", href=True)
            if not link:
                continue

            href = urljoin(self.base_url, link.get("href", ""))
            if not href.startswith(self.base_url) or "/video/" in href:
                continue

            title = self._clean_text(link.get("title") or link.get_text())
            if not title:
                continue

            # Summary: next sibling paragraph or a nearby .sapo/summary class
            summary = ""
            next_sibling = tag.find_next_sibling()
            if next_sibling and next_sibling.name == "p":
                summary = self._clean_text(next_sibling.get_text())
            else:
                container = tag.find_parent(["article", "div", "li"])
                if container:
                    p = container.find("p")
                    if p:
                        summary = self._clean_text(p.get_text())
                    else:
                        sapo = container.find(class_=re.compile("sapo|summary|des|lead"))
                        if sapo:
                            summary = self._clean_text(sapo.get_text())

            published_at_text = None
            # VietStock puts the relative/absolute date in the title attribute of a
            # small meta link, e.g. "4 giờ trước" or "04/07 19:00".
            container = tag.find_parent(["article", "div", "li"])
            if container:
                meta = container.find(class_=re.compile("meta\d*|meta"))
                if meta:
                    time_link = meta.find("a", href=True, title=True)
                    if time_link:
                        published_at_text = self._clean_text(time_link.get("title", ""))
            if not published_at_text:
                time_tag = tag.find_next("time")
                if time_tag:
                    published_at_text = self._clean_text(
                        time_tag.get_text() or time_tag.get("datetime", "")
                    )
            if not published_at_text:
                time_span = tag.find_next(class_=re.compile("time|date|hour"))
                if time_span:
                    published_at_text = self._clean_text(time_span.get_text())

            items.append(
                {
                    "url": href,
                    "title": title,
                    "summary": summary,
                    "published_at": self._parse_time(published_at_text),
                    "published_at_text": published_at_text,
                }
            )

        return items

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())
