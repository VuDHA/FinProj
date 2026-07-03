import datetime
import json
from unittest.mock import MagicMock, patch

import requests

from common.models import Asset, Income, NewsArticle, NewsSource, NewsSymbol, Transaction, Watchlist
from services.ai.embedding_store import EmbeddingStore
from common.env_config import get_env_config, update_env_config
from services.market.gold_fx import get_gold_fx
from services.market.market_data import MarketDataService
from services.ai.ollama_client import OllamaClient, OllamaClientError
from services.ai.rag_context import RagContextService
from services.market.source_config import (
    get_asset_source_params,
    get_default_sources,
    is_valid_source_for_type,
    seed_default_sources,
    set_default_sources,
)
from services.market.source_selector import SourceSelector
from services.market.sources.base import Source, SourceRegistry
from sqlmodel import select


class FakeSource(Source):
    code = "fake"
    name = "Fake"
    description = "Fake source"
    supported_types = ["STOCK"]
    supports_history = True
    supports_listing = True

    def fetch_price(self, asset):
        return {
            "price": 100,
            "change": 1,
            "change_percent": 1,
            "date": datetime.date.today(),
        }

    def fetch_history(self, symbol, asset_type, start, end):
        return {datetime.date.today(): 100}

    def fetch_listing(self):
        return [{"symbol": "FAKE", "name": "Fake", "exchange": "HOSE", "type": "STOCK"}]


class FakeRegistry:
    def __init__(self, sources):
        self._sources = {s.code: s for s in sources}

    def get(self, code):
        return self._sources.get(code)

    def for_type(self, asset_type):
        return [s for s in self._sources.values() if asset_type in s.supported_types]


class FakeFundSource(Source):
    code = "fakefund"
    name = "Fake Fund"
    description = "Fake fund source"
    supported_types = ["FUND"]

    def fetch_price(self, asset):
        return {"price": 100, "date": datetime.date.today()}

    def fetch_fund_detail(self, symbol):
        return {"symbol": symbol, "name": "Fake Fund", "nav": 100, "fund_type": "BALANCED"}


def _fake_registry(sources):
    return FakeRegistry(sources)


def test_source_selector_fetch_price(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    selector = SourceSelector(session)
    asset = Asset(symbol="VCB", type="STOCK", name="VCB")
    data, warnings = selector.fetch_price(asset)
    assert data["price"] == 100
    assert not warnings


def test_source_selector_fetch_history(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    selector = SourceSelector(session)
    asset = Asset(symbol="VCB", type="STOCK", name="VCB")
    hist = selector.fetch_history(asset, datetime.date.today(), datetime.date.today())
    assert hist[datetime.date.today()] == 100


def test_source_selector_fetch_listing(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    selector = SourceSelector(session)
    listings = selector.fetch_listing("STOCK")
    assert len(listings) == 1


def test_source_selector_fallback_to_default(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    selector = SourceSelector(session)
    asset = Asset(symbol="VCB", type="STOCK", name="VCB")
    data, _ = selector.fetch_price(asset)
    assert data["price"] == 100


def test_source_config_defaults(session):
    defaults = get_default_sources(session)
    assert defaults["STOCK"] == "kbs"
    assert defaults["FUND"] == "fmarket"


def test_source_config_seed_and_set(session):
    seed_default_sources(session)
    result = set_default_sources(session, {"STOCK": "cafef"})
    assert result["STOCK"] == "cafef"


def test_source_config_is_valid_source(session):
    assert is_valid_source_for_type("kbs", "STOCK") is True
    assert is_valid_source_for_type("kbs", "GOLD") is False


def test_get_asset_source_params():
    asset = Asset(symbol="VCB", name="VCB", type="STOCK", source_params='{"key": "value"}')
    assert get_asset_source_params(asset) == {"key": "value"}
    asset.source_params = "not json"
    assert get_asset_source_params(asset) is None


def test_env_config_get(client):
    response = client.get("/api/v1/settings/env-config")
    assert response.status_code == 200


def test_env_config_update(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OLLAMA_ENABLED=true\n")
    monkeypatch.setattr("common.env_config._ENV_PATH", env_file)
    result = update_env_config({"OLLAMA_ENABLED": "false"})
    assert result["requires_restart"] is False
    assert env_file.read_text().strip().endswith("OLLAMA_ENABLED=false")


def test_gold_fx_with_mocked_requests(monkeypatch):
    def fake_get(url, **kwargs):
        response = MagicMock()
        if "vang.today" in url:
            response.status_code = 200
            response.json.return_value = {
                "prices": {"SJC": {"name": "SJC", "buy": 70000, "sell": 71000}}
            }
        elif "vietcombank" in url:
            response.status_code = 200
            response.content = b'<root><Exrate CurrencyCode="USD" Buy="23000" Transfer="23500" Sell="24000"/></root>'
            response.text = response.content.decode()
        else:
            response.status_code = 200
            response.json.return_value = {"rates": {"VND": 23500}}
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    result = get_gold_fx()
    assert len(result.gold) >= 1
    assert len(result.fx) >= 1


def test_market_data_fetch_price(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._resolve_asset_source", lambda self, asset: "fake"
    )
    service = MarketDataService(session)
    asset = Asset(symbol="VCB", type="STOCK", name="VCB")
    data = service.fetch_price(asset)
    assert data["price"] == 100


def test_market_data_fetch_quote(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._resolve_asset_source", lambda self, asset: "fake"
    )
    service = MarketDataService(session)
    quote = service.fetch_quote("VCB", "STOCK")
    assert quote["price"] == 100


def test_market_data_fetch_quotes_for_assets(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._resolve_asset_source", lambda self, asset: "fake"
    )
    service = MarketDataService(session)
    asset = Asset(symbol="VCB", type="STOCK", name="VCB")
    quotes = service.fetch_quotes_for_assets([asset])
    assert len(quotes) == 1
    assert quotes[0]["symbol"] == "VCB"


def test_market_data_fetch_history(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._resolve_asset_source", lambda self, asset: "fake"
    )
    service = MarketDataService(session)
    today = datetime.date.today()
    hist = service.fetch_history("VCB", "STOCK", today, today)
    assert hist[today] == 100


def test_market_data_fetch_all_symbols(session, monkeypatch):
    monkeypatch.setattr("services.market.source_selector.registry", _fake_registry([FakeSource()]))
    monkeypatch.setattr(
        "services.market.source_selector.SourceSelector._get_defaults", lambda self: {"STOCK": "fake"}
    )
    service = MarketDataService(session)
    symbols = service.fetch_all_symbols()
    assert len(symbols) == 1


def test_market_data_fetch_fund_detail(monkeypatch):
    monkeypatch.setattr(
        "services.market.market_data.registry", _fake_registry([FakeFundSource()])
    )
    service = MarketDataService.__new__(MarketDataService)
    detail = service.fetch_fund_detail("E1VFVN30")
    assert detail["symbol"] == "E1VFVN30"
    assert detail["nav"] == 100


def test_market_data_fetch_benchmark_history(monkeypatch):
    # Use a fixed UTC noon timestamp so the service's UTC date conversion is deterministic.
    sample_ts = int(datetime.datetime(2023, 1, 15, 12, 0, tzinfo=datetime.timezone.utc).timestamp())
    expected_date = datetime.datetime.fromtimestamp(sample_ts, tz=datetime.timezone.utc).date()

    def fake_get(url, params=None, **kwargs):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"t": [sample_ts], "c": [1000]}
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    service = MarketDataService.__new__(MarketDataService)
    service._BENCHMARK_CACHE.clear()
    service._BENCHMARK_CACHE_TIME = None
    hist = service.fetch_benchmark_history("VNINDEX", expected_date, expected_date)
    assert hist[expected_date] == 1000


def test_embedding_store_serialize_and_deserialize():
    store = EmbeddingStore(enabled=False)
    vector = [0.1, 0.2, 0.3]
    serialized = store._serialize(vector)
    assert isinstance(serialized, str)
    assert store._deserialize(serialized) == vector


def test_embedding_store_create_embedding_disabled():
    store = EmbeddingStore(enabled=False)
    assert store.create_embedding(1, "test") is None


def test_embedding_store_find_similar_for_text_disabled():
    store = EmbeddingStore(enabled=False)
    assert store.find_similar_for_text("query") == []


def test_ollama_client_generate_success(monkeypatch):
    def fake_post(url, json=None, **kwargs):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"response": "hello"}
        response.raise_for_status.return_value = None
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaClient(base_url="http://localhost", timeout=1)
    assert client.generate("hi") == "hello"


def test_ollama_client_embed_success(monkeypatch):
    def fake_post(url, json=None, **kwargs):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        response.raise_for_status.return_value = None
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    client = OllamaClient(base_url="http://localhost", timeout=1)
    assert client.embed("hi") == [0.1, 0.2, 0.3]


def test_ollama_client_generate_error(monkeypatch):
    from services.ai.ai_queue import AIQueueBusyError

    def fake_run(self, name, task):
        raise AIQueueBusyError("busy")

    monkeypatch.setattr("services.ai.ai_queue.AIQueue.run", fake_run)
    client = OllamaClient(base_url="http://localhost", timeout=1)
    try:
        client.generate("hi")
        assert False, "expected OllamaClientError"
    except OllamaClientError:
        pass


def test_rag_context_user_facts(session):
    asset = Asset(symbol="VCB", name="VCB", type="STOCK")
    session.add(asset)
    session.commit()
    session.refresh(asset)

    session.add(Watchlist(symbol="VCB"))
    session.add(Transaction(asset_id=asset.id, type="BUY", quantity=10, price=100, fee=0, date=datetime.date(2023, 1, 1)))
    session.add(Income(asset_id=asset.id, type="DIVIDEND", amount=50, date=datetime.date(2023, 1, 1)))
    session.commit()

    store = EmbeddingStore(enabled=False)
    service = RagContextService(session, embedding_store=store)
    facts = service.user_facts()
    assert "VCB" in facts["portfolio_symbols"]
    assert "VCB" in facts["watchlist"]
    assert len(facts["recent_transactions"]) == 1


def test_rag_context_build_and_format_context(session):
    store = EmbeddingStore(enabled=False)
    service = RagContextService(session, embedding_store=store)
    context = service.build_context("title", "summary")
    assert "user_facts" in context
    assert "similar_articles" in context
    assert context["similar_articles"] == []
    formatted = service.format_context(context, language="en")
    assert "User context" in formatted or formatted == ""
