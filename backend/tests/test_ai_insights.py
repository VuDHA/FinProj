from unittest.mock import patch

import pytest

from common.schemas import BacktestRequest
from services.ai.ai_insights.base_prompt import master_prompt
from services.ai.ai_insights.prompts import base_prompt, minify_dict


def test_master_prompt_is_concise():
    text = master_prompt("vi")
    assert "CHỈ trả về" in text
    assert "không chào hỏi" in text.lower()
    assert len(text) < 300


def test_minify_dict_keeps_only_requested_fields():
    data = [
        {"symbol": "VCB", "type": "STOCK", "extra": "drop", "current_value": 1000},
        {"symbol": "VNM", "type": "STOCK", "noise": 123, "current_value": 2000},
    ]
    compact = minify_dict(data, ["symbol", "current_value"])
    assert compact == [
        {"symbol": "VCB", "current_value": 1000},
        {"symbol": "VNM", "current_value": 2000},
    ]


def test_base_prompt_includes_strict_json_instruction():
    prompt = base_prompt("data", "role", "context")
    assert "CHỈ trả về đúng đầu ra" in prompt
    assert '{"overall":"...","details":"...","suggestions":["...","..."]}' in prompt


@pytest.fixture
def mock_insight(monkeypatch):
    targets = [
        "services.ai.ai_insights.portfolio.generate_insight",
        "services.ai.ai_insights.analytics.generate_insight",
        "services.ai.ai_insights.rebalance.generate_insight",
        "services.ai.ai_insights.market.generate_insight",
        "services.ai.ai_insights.compare.generate_insight",
    ]
    for target in targets:
        monkeypatch.setattr(
            target,
            lambda *args, **kwargs: {
                "overall": "Tổng quan mẫu",
                "details": "Chi tiết mẫu",
                "suggestions": ["Gợi ý mẫu"],
                "used_ollama": False,
            },
        )


def test_ai_rate_limit_endpoint(client):
    response = client.get("/api/v1/ai/rate-limit")
    assert response.status_code == 200
    data = response.json()
    assert "gemini_generation" in data
    assert "gemini_embedding" in data
    assert "ollama_generation" in data
    assert "ollama_embedding" in data
    for provider in data.values():
        assert "max_rpm" in provider
        assert "max_concurrent" in provider
        assert "available_rpm" in provider
        assert "available_concurrent" in provider


def test_portfolio_ai_insight_endpoint(client, session, mock_insight):
    from common.models import Asset

    session.add(Asset(symbol="VCB", name="Vietcombank", type="STOCK", is_active=True))
    session.commit()

    response = client.post("/api/v1/portfolio/ai-insight")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "details" in data
    assert "suggestions" in data


def test_analytics_ai_insight_endpoint(client, mock_insight):
    response = client.post("/api/v1/analytics/ai-insight")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "details" in data
    assert "suggestions" in data


def test_rebalance_ai_insight_endpoint(client, mock_insight):
    response = client.post("/api/v1/rebalance/ai-insight")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "details" in data
    assert "suggestions" in data


def test_compare_ai_insight_endpoint(client, mock_insight):
    payload = {
        "symbols": ["VCB", "VNM"],
        "metrics": [
            {
                "symbol": "VCB",
                "total_return": 10.0,
                "annualized_return": 5.0,
                "volatility": 15.0,
                "max_drawdown_percent": -8.0,
                "sharpe_ratio": 0.5,
            },
            {
                "symbol": "VNM",
                "total_return": 8.0,
                "annualized_return": 4.0,
                "volatility": 18.0,
                "max_drawdown_percent": -10.0,
                "sharpe_ratio": 0.4,
            },
        ],
        "correlation": {
            "labels": ["VCB", "VNM"],
            "matrix": [[1.0, 0.8], [0.8, 1.0]],
        },
    }
    response = client.post("/api/v1/compare/ai-insight", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "details" in data
    assert "suggestions" in data


def test_market_ai_insight_endpoint(client, mock_insight):
    from api import prices as prices_api
    from services.market.market_data import MarketDataService
    from common.schemas import GoldFxResponse

    with patch.object(
        MarketDataService,
        "fetch_quotes",
        return_value=[{"symbol": "VCB", "price": 100, "change": 0, "change_percent": 0, "date": "2023-01-01"}],
    ):
        with patch.object(
            prices_api,
            "get_gold_fx",
            return_value=GoldFxResponse(gold=[], fx=[]),
        ):
            response = client.post("/api/v1/prices/market-ai-insight")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "details" in data
    assert "suggestions" in data


def test_compare_ai_insight_requires_two_symbols(client):
    payload = {
        "symbols": ["VCB"],
        "metrics": [],
        "correlation": {"labels": ["VCB"], "matrix": [[1.0]]},
    }
    response = client.post("/api/v1/compare/ai-insight", json=payload)
    assert response.status_code == 400


def test_backtest_ai_stress_endpoint(client, session):
    import datetime

    from common.models import Asset, PriceSnapshot

    asset = Asset(symbol="VCB", name="Vietcombank", type="STOCK", is_active=True)
    session.add(asset)
    session.commit()
    session.refresh(asset)

    for i in range(31):
        date = datetime.date(2023, 1, 1) + datetime.timedelta(days=i)
        session.add(
            PriceSnapshot(
                asset_id=asset.id,
                date=date,
                price=100000.0 + i * 100,
                change=0,
                change_percent=0,
            )
        )
    session.commit()

    mock_request = BacktestRequest(
        symbols=["VCB"],
        start_date="2023-01-01",
        end_date="2023-01-31",
        strategy="buy_and_hold",
        rebalance_frequency="monthly",
        initial_cash=100000000,
    )
    with patch(
        "services.ai.prompt_parser.PromptParser.parse_stress_prompt",
        return_value=mock_request,
    ):
        response = client.post(
            "/api/v1/backtest/ai-stress",
            json={"prompt": "kiểm thử khủng hoảng VCB", "base_request": None},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["request"]["symbols"] == ["VCB"]
    assert "result" in data
