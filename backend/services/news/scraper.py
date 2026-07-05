import random
import re
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class ArticleScraperError(Exception):
    """Raised when an article cannot be scraped or parsed."""

    pass


class ArticleScraper:
    """Lightweight article content extractor using requests + BeautifulSoup.

    Tries to extract the main article text from a URL. This is intentionally
    simple and dependency-light; it does not handle every site layout, but it
    works well for typical Vietnamese and global finance news publishers.

    For hard-to-scrape sites (Bloomberg, Investing.com, etc.) that return 403
    or 503, the scraper falls back to extracting whatever metadata is available
    and returns a *partial* result so the caller can still produce a short
    title-based summary instead of failing completely.
    """

    _user_agents = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
    ]

    # Common content selectors ordered by preference. Vietnamese news sites
    # often use #mainContent, .detail-content, .sapo, or article tags.
    _content_selectors = [
        "article",
        '[itemprop="articleBody"]',
        ".article-body",
        ".article-content",
        ".detail-content",
        ".post-content",
        ".content-detail",
        ".entry-content",
        ".main-content",
        ".content-main",
        "#mainContent",
        "#article-content",
        "#articleBody",
        "#content_detail",
        "#abody",
        "main",
        ".content",
        "#content",
    ]

    _title_selectors = ["h1", ".article-title", ".title", ".news-title"]

    _summary_selectors = [
        ".sapo",
        ".description",
        ".lead",
        ".summary",
        ".article-summary",
        '[name="description"]',
    ]

    def __init__(
        self,
        timeout: int = 30,
        max_length: int = 8000,
        retries: int = 2,
        retry_delay: float = 1.5,
    ):
        self.timeout = timeout
        self.max_length = max_length
        self.retries = retries
        self.retry_delay = retry_delay

    def scrape(self, url: str) -> Dict[str, Optional[str]]:
        """Fetch a URL and return a dict with title, summary, and content_text.

        If the site blocks the request, we still try to extract the title and
        meta description from the returned HTML and mark the result as partial.
        """
        if not url or not url.startswith(("http://", "https://")):
            raise ArticleScraperError(f"Invalid URL: {url}")

        response, last_error = None, None
        for attempt in range(self.retries + 1):
            try:
                response = self._fetch(url, attempt)
                break
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retries and self._is_retriable(e):
                    time.sleep(self.retry_delay * (attempt + 1) + random.uniform(0, 1))
                else:
                    break

        if response is None:
            raise ArticleScraperError(f"Failed to fetch {url}: {last_error}") from last_error

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        title = self._extract_title(soup)
        summary = self._extract_summary(soup)
        content_text = self._extract_content(soup)
        blocked = response.status_code in (403, 503, 429) or self._is_bot_page(soup)
        partial = False

        if blocked:
            # The full article body is not available; ignore anything that looks
            # like a challenge page and work with the title/meta description.
            content_text = None
            partial = True

        if not content_text and summary:
            content_text = summary
        if not content_text and not summary:
            # Last resort: try to keep the title alive so the caller can still
            # produce a short summary from the headline.
            partial = True
            content_text = title

        if not content_text:
            raise ArticleScraperError(
                f"Could not extract readable content from {url} (status {response.status_code})"
            )

        return {
            "title": title,
            "summary": summary,
            "content_text": content_text[: self.max_length],
            "url": url,
            "partial": partial,
            "status_code": response.status_code,
        }

    def _fetch(self, url: str, attempt: int) -> requests.Response:
        """Fetch with browser-like headers and cookies."""
        session = requests.Session()
        headers = {
            "User-Agent": random.choice(self._user_agents),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        if attempt == 0:
            headers["Referer"] = "https://www.google.com/"
        else:
            headers["Referer"] = f"https://{self.domain(url)}/"

        response = session.get(
            url,
            timeout=self.timeout,
            headers=headers,
            allow_redirects=True,
        )
        # Don't raise immediately for 403/503; sometimes the returned HTML still
        # contains title/meta description we can use.
        if response.status_code not in (403, 503, 429) and response.status_code >= 400:
            response.raise_for_status()
        return response

    def _is_retriable(self, error: requests.RequestException) -> bool:
        response = getattr(error, "response", None)
        if response is not None:
            return response.status_code in (429, 500, 502, 503, 504)
        return isinstance(error, (requests.Timeout, requests.ConnectionError))

    @staticmethod
    def _is_bot_page(soup: BeautifulSoup) -> bool:
        """Detect Cloudflare / bot-protection challenge pages."""
        page_text = ""
        if soup.title and soup.title.string:
            page_text += " " + str(soup.title.string)
        body = soup.find("body")
        if body:
            page_text += " " + body.get_text(" ", strip=True)[:800]
        page_text = page_text.lower()
        signals = [
            "just a moment",
            "attention required",
            "cloudflare",
            "verify you are human",
            "ddos protection",
            "403 forbidden",
            "access denied",
            "blocked",
            "please wait",
            "checking your browser",
            "security check",
        ]
        return any(signal in page_text for signal in signals)

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        # Prefer og:title, then page title, then visible h1/headlines.
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            text = self._clean_text(og_title.get("content"))
            if text:
                return text
        if soup.title and soup.title.string:
            title = self._clean_text(soup.title.string)
            if title:
                return title
        for selector in self._title_selectors:
            tag = soup.select_one(selector)
            if tag:
                text = self._clean_text(tag.get_text())
                if text:
                    return text
        return None

    def _extract_summary(self, soup: BeautifulSoup) -> Optional[str]:
        # Try og:description, then meta description, then visible summary elements.
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            text = self._clean_text(og_desc.get("content"))
            if text:
                return text

        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            text = self._clean_text(meta.get("content"))
            if text:
                return text

        for selector in self._summary_selectors:
            tag = soup.select_one(selector)
            if tag:
                text = self._clean_text(tag.get_text())
                if text:
                    return text
        return None

    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in self._content_selectors:
            container = soup.select_one(selector)
            if container:
                text = self._clean_text(container.get_text())
                if len(text) > 100:
                    return text

        # Fallback: use the body but drop noisy tags.
        body = soup.find("body")
        if body:
            text = self._clean_text(body.get_text())
            if len(text) > 200:
                return text
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\xa0", " ")
        return text.strip()

    @staticmethod
    def domain(url: str) -> str:
        return urlparse(url).netloc
