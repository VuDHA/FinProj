import datetime
import re
from typing import Dict, List, Optional, Set

from sqlmodel import Session

from services.news.dictionaries import analyze_impact, analyze_sentiment, get_known_symbols
from services.news.tagging import TaggingService
from services.rag_context import RagContextService


class NewsProcessor:
    """Rule-based processor that enriches raw articles with symbols, tags, sentiment, and impact."""

    def __init__(
        self,
        known_symbols: Optional[Set[str]] = None,
        session: Optional[Session] = None,
    ):
        self.known_symbols = known_symbols or get_known_symbols()
        self.session = session
        rag_context = None
        if session is not None:
            try:
                rag = RagContextService(session)
                rag_context = rag.format_context(
                    rag.build_context(include_user_facts=True, include_similar_articles=False),
                    language="vi",
                )
            except Exception as e:
                print(f"[news:processor] failed to build RAG context: {e}")
        self._tagger = TaggingService(context=rag_context)

    # Vietnamese/English terms that are not stock symbols but match ticker patterns
    _STOP_WORDS: Set[str] = {
        "ALL", "AND", "ANY", "ARE", "ASK", "ASX", "BA", "BAN", "BAT", "BAY",
        "BID", "BOI", "BON", "BOY", "BUON", "BUT", "CA", "CAC", "CAN", "CANG",
        "CAO", "CEO", "CFO", "CH", "CHI", "CHIN", "CHINH", "CHO", "CHUNG", "CNY",
        "CO", "COM", "CON", "CONG", "COO", "CPI", "CTO", "CUA", "CUNG", "DA",
        "DAN", "DANG", "DAU", "DAX", "DAY", "DE", "DEN", "DI", "DICH", "DID",
        "DIEN", "DJI", "DJIA", "DO", "DOANH", "DONG", "DOW", "DU", "DUNG", "DUOC",
        "DUOI", "EPS", "ETF", "EU", "EUR", "FED", "FOR", "FTSE", "GDP", "GET",
        "GH", "GI", "GIAM", "GIAO", "GIAY", "GIO", "GIUA", "HAD", "HAI", "HANG",
        "HAS", "HAY", "HER", "HIEN", "HIM", "HIS", "HNX", "HO", "HOA", "HOAC",
        "HOACH", "HOI", "HOM", "HON", "HOP", "HOSE", "HOW", "HSX", "HTML", "HTTP",
        "HTTPS", "INTERNET", "IPO", "ITS", "JPY", "JSON", "KE", "KH", "KHAU", "KHI",
        "KHOAN", "KHONG", "KINH", "KOSPI", "KY", "LA", "LAI", "LE", "LEN", "LET",
        "LOI", "MA", "MAI", "MAN", "MO", "MOI", "MOT", "MUA", "MUC", "MUOI",
        "NAM", "NASDAQ", "NAV", "NAY", "NEN", "NEU", "NEW", "NG", "NGAN", "NGAY",
        "NGH", "NGHIN", "NGOAI", "NGUOI", "NH", "NHAN", "NHAP", "NHIEU", "NHU", "NHUAN",
        "NHUNG", "NIKKEI", "NO", "NOI", "NOT", "NOW", "NUOC", "NYSE", "OLD", "ONE",
        "OUR", "OUT", "PB", "PE", "PH", "PHAI", "PHAN", "PHI", "PHUT", "PPI",
        "PUT", "QU", "QUY", "RA", "RAT", "REIT", "RO", "ROE", "ROI", "RSS",
        "S&P", "SAN", "SAU", "SAY", "SE", "SEE", "SEN", "SENG", "SHE", "SINH",
        "SO", "SP500", "SU", "SUAT", "TAC", "TAI", "TAM", "TANG", "TAO", "TAT",
        "TE", "TEU", "TH", "THANG", "THANH", "THAP", "THAU", "THE", "THI", "THOAI",
        "THU", "THUC", "THUE", "THUONG", "TIEN", "TIN", "TINH", "TO", "TOO", "TR",
        "TRAM", "TREN", "TRIEU", "TRONG", "TRUOC", "TRUONG", "TSX", "TU", "TUAN", "TUC",
        "TUNG", "TWO", "TY", "UK", "UPCOM", "US", "USA", "USD", "USE", "VA",
        "VAN", "VAO", "VAT", "VAY", "VE", "VI", "VIET", "VIETNAM", "VN", "VND",
        "VNINDEX", "VO", "VON", "VONG", "VU", "VUA", "WAS", "WAY", "WHO", "WWW",
        "XA", "XAY", "XML", "XUAT", "XUONG", "YOU",
}

    def _is_valid_symbol(self, token: str, check_stop_words: bool = True) -> bool:
        """Validate a potential symbol token.

        Known symbols skip the stop-word check so real tickers that happen to
        collide with common words (e.g. SAN, THI, NHU) are still extracted.
        """
        if not token or len(token) > 8 or len(token) < 2:
            return False
        if not re.match(r"^[A-Z0-9\.\-]+$", token):
            return False
        # Exclude pure numeric tokens (dates, times, percentages, prices)
        if re.match(r"^[0-9]+$", token):
            return False
        if check_stop_words and token in self._STOP_WORDS:
            return False
        return True

    def extract_symbols(self, text: str) -> List[str]:
        """Extract mentioned stock/crypto symbols from text.

        Stock symbols are normally written in uppercase, so we only match
        uppercase tokens. This avoids treating Vietnamese consonant clusters
        ("KH" inside "khí"), English words, and numbers as tickers.
        """
        if not text:
            return []

        found: Set[str] = set()

        # Look for known symbols. Require word boundaries so "V" inside "Việt" is
        # not matched, and require the symbol to appear in uppercase.
        for symbol in self.known_symbols:
            if self._is_valid_symbol(symbol, check_stop_words=False) and symbol in text:
                pattern = r"\b" + re.escape(symbol) + r"\b"
                if re.search(pattern, text):
                    found.add(symbol)

        # Unknown candidates: all-uppercase, standalone tokens that look like
        # tickers (e.g., 2-8 chars, start with a letter).
        tokens = re.findall(r"\b[A-Z][A-Z0-9\-\.]{1,7}\b", text)
        for token in tokens:
            if self._is_valid_symbol(token) and token not in found:
                found.add(token)

        return sorted(found)

    def process(self, article: Dict) -> Dict:
        """Enrich a normalized article with symbols, sentiment, impact, and summary."""
        text = " ".join(
            filter(
                None,
                [
                    article.get("title", ""),
                    article.get("summary", ""),
                    article.get("content_text", ""),
                ],
            )
        )
        language = article.get("language", "vi")

        symbols = self.extract_symbols(text)
        sentiment = analyze_sentiment(text, language)
        impact = analyze_impact(text, language)

        # Generate a simple extractive summary if none provided
        summary = article.get("summary")
        if not summary and article.get("content_text"):
            sentences = re.split(r"(?<=[.!?])\s+", article["content_text"])
            summary = " ".join(sentences[:2]).strip()
            if len(summary) > 500:
                summary = summary[:500] + "..."

        tags = self._tagger.generate(article) if not article.get("tags") else []
        processed = dict(article)
        processed["symbols"] = symbols
        processed["tags"] = article.get("tags") or self._tagger.join(tags)
        processed["sentiment_score"] = round(sentiment, 2)
        processed["impact_score"] = round(impact, 2)
        processed["summary"] = summary
        processed["fetched_at"] = datetime.datetime.utcnow()
        return processed

    def process_many(self, articles: List[Dict]) -> List[Dict]:
        """Process a list of articles."""
        return [self.process(a) for a in articles]
