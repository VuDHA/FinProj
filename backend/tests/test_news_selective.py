import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine

from models import NewsArticle, NewsSource
from services.news.feed import NewsFeedService
from services.news.relevance import RelevanceScorer
from services.news.sources.base import NewsSourceAdapter
from services.news.sources.intl.bloomberg import BloombergNewsSource
from services.news.sources.intl.investing import InvestingNewsSource
from services.news.sources.intl.yahoo_finance import YahooFinanceNewsSource
from services.news.sources.vn.cafef import CafeFNewsSource
from services.news.sources.vn.thoibaotaichinhvietnam import ThoiBaoTaiChinhVietNamNewsSource
from services.news.sources.vn.vietstock import VietStockNewsSource
from services.news.sources import registry


class DummySource(NewsSourceAdapter):
    code = "dummy"
    name = "Dummy"
    language = "vi"
    region = "vn"

    def fetch(self):
        return []


def test_adapter_normalization_includes_region():
    adapter = DummySource()
    normalized = adapter.normalize({"url": "https://example.com/1", "title": "Tin"})
    assert normalized["region"] == "vn"
    assert normalized["language"] == "vi"


def test_bloomberg_source_is_global():
    source = BloombergNewsSource()
    assert source.region == "global"
    assert source.code == "bloomberg"


def test_cafef_source_is_vn():
    source = CafeFNewsSource()
    assert source.region == "vn"
    assert source.code == "cafef"


def test_relevance_scorer_rule_based_vn():
    scorer = RelevanceScorer(enabled=False)
    article = {
        "title": "VN-Index tăng mạnh nhờ cổ phiếu ngân hàng",
        "summary": "Thị trường chứng khoán Việt Nam hôm nay ghi nhận sắc xanh.",
        "category": "chung-khoan",
        "region": "vn",
        "symbols": ["VCB"],
        "sentiment_score": 0.3,
        "impact_score": 0.6,
    }
    result = scorer.score(article)
    assert 0.0 <= result["relevance_score"] <= 1.0
    assert result["is_standout"] is True


def test_relevance_scorer_rule_based_global():
    scorer = RelevanceScorer(enabled=False)
    article = {
        "title": "Federal Reserve keeps interest rates steady",
        "summary": "Markets react to the latest Fed decision.",
        "category": "markets",
        "region": "global",
        "symbols": [],
        "sentiment_score": 0.0,
        "impact_score": 0.4,
    }
    result = scorer.score(article)
    assert 0.0 <= result["relevance_score"] <= 1.0


def test_feed_service_filters_by_region():
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        vn_source = NewsSource(code="cafef", name="CafeF", region="vn")
        global_source = NewsSource(code="bloomberg", name="Bloomberg", region="global")
        session.add(vn_source)
        session.add(global_source)
        session.flush()

        vn_article = NewsArticle(
            source_id=vn_source.id,
            url="https://cafef.vn/1",
            title="Tin VN",
            region="vn",
            is_standout=True,
            is_active=True,
        )
        global_article = NewsArticle(
            source_id=global_source.id,
            url="https://bloomberg.com/1",
            title="Global News",
            region="global",
            is_standout=True,
            is_active=True,
        )
        session.add(vn_article)
        session.add(global_article)
        session.commit()

        service = NewsFeedService(session)
        vn_items = service.list_articles(region="vn", limit=10)
        global_items = service.list_articles(region="global", limit=10)

        assert len(vn_items) == 1
        assert vn_items[0].region == "vn"
        assert len(global_items) == 1
        assert global_items[0].region == "global"


def test_vietstock_source_is_vn():
    source = VietStockNewsSource()
    assert source.region == "vn"
    assert source.code == "vietstock"
    assert source.language == "vi"


def test_tbtcvn_source_is_vn():
    source = ThoiBaoTaiChinhVietNamNewsSource()
    assert source.region == "vn"
    assert source.code == "tbtcvn"
    assert source.language == "vi"


def test_investing_source_is_global():
    source = InvestingNewsSource()
    assert source.region == "global"
    assert source.code == "investing"
    assert source.language == "en"


def test_new_sources_are_registered():
    codes = registry.codes()
    assert "vietstock" in codes
    assert "tbtcvn" in codes
    assert "investing" in codes


def test_investing_filters_non_finance_urls():
    source = InvestingNewsSource()
    assert source._is_finance_url("https://www.investing.com/news/stock-market-news/foo-1") is True
    assert source._is_finance_url("https://www.investing.com/news/economy-news/foo-1") is True
    assert source._is_finance_url("https://www.investing.com/news/world-news/foo-1") is False
    assert source._is_finance_url("https://example.com/news/stock-market-news/foo-1") is False


def test_parse_time_vietnamese_day_name():
    parsed = NewsSourceAdapter._parse_time("Chủ nhật 05/07/2026 00:10")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 7
    assert parsed.day == 5
    assert parsed.hour == 0
    assert parsed.minute == 10


def test_parse_time_relative_hours():
    before = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    parsed = NewsSourceAdapter._parse_time("3 giờ trước")
    assert parsed is not None
    assert before - datetime.timedelta(minutes=1) <= parsed <= before + datetime.timedelta(minutes=1)


def test_parse_time_date_only_uses_current_year():
    parsed = NewsSourceAdapter._parse_time("04/07")
    assert parsed is not None
    assert parsed.month == 7
    assert parsed.day == 4
    assert parsed.year == datetime.datetime.utcnow().year


def test_parse_time_from_url():
    parsed = NewsSourceAdapter._parse_time_from_url(
        "https://vietstock.vn/2026/07/chung-khoan-foo-123.htm"
    )
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 7
    assert parsed.day == 1


def test_parse_time_from_url_full_day():
    parsed = NewsSourceAdapter._parse_time_from_url(
        "https://example.com/news/2026/07/05/article.html"
    )
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 7
    assert parsed.day == 5


def test_resolve_published_at_falls_back_to_now():
    before = datetime.datetime.utcnow()
    parsed = NewsSourceAdapter._resolve_published_at(text=None, url=None)
    after = datetime.datetime.utcnow()
    assert before <= parsed <= after


def test_normalize_never_returns_null_published_at():
    class DummySource(NewsSourceAdapter):
        code = "dummy"
        name = "Dummy"
        language = "vi"
        region = "vn"

        def fetch(self):
            return []

    source = DummySource()
    normalized = source.normalize({
        "url": "https://example.com/2026/07/article.html",
        "title": "Tin",
        "published_at": None,
        "published_at_text": None,
    })
    assert normalized["published_at"] is not None
    assert isinstance(normalized["published_at"], datetime.datetime)
