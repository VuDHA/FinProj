import pytest
from sqlmodel import Session, SQLModel, create_engine

from common.models import NewsArticle, NewsSource
from services.news.feed import NewsFeedService
from services.news.relevance import RelevanceScorer
from services.news.sources.base import NewsSourceAdapter
from services.news.sources.intl.bloomberg import BloombergNewsSource
from services.news.sources.vn.cafef import CafeFNewsSource


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
