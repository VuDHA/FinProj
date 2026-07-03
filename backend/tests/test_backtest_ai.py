from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from common.models import Asset
from common.schemas import BacktestRequest
from services.ai.prompt_parser import PromptParser, PromptParserError


def test_backtest_ai_parses_prompt_and_runs(client, session):
    # Create an active asset for the backtest to use.
    session.add(Asset(symbol="VCB", name="Vietcombank", type="STOCK", is_active=True))
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
        "services.ai.prompt_parser.PromptParser.parse_backtest_prompt",
        return_value=mock_request,
    ):
        response = client.post("/api/v1/backtest/ai", json={"prompt": "kiểm thử VCB tháng 1/2023"})

    assert response.status_code == 200
    data = response.json()
    assert data["request"]["symbols"] == ["VCB"]
    assert "result" in data


def test_backtest_ai_creates_unknown_symbols_on_the_fly(client, session):
    from common.models import Asset

    mock_request = BacktestRequest(
        symbols=["XYZABC"],
        start_date="2023-01-01",
        end_date="2023-01-31",
        strategy="buy_and_hold",
        rebalance_frequency="monthly",
        initial_cash=100000000,
    )

    with patch(
        "services.ai.prompt_parser.PromptParser.parse_backtest_prompt",
        return_value=mock_request,
    ):
        response = client.post(
            "/api/v1/backtest/ai",
            json={"prompt": "kiểm thử mã không tồn tại XYZABC"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["request"]["symbols"] == ["XYZABC"]
    assert "result" in data

    # Verify the asset was auto-created
    asset = session.exec(select(Asset).where(Asset.symbol == "XYZABC")).first()
    assert asset is not None
    assert asset.type == "STOCK"
    assert asset.is_active is True


def test_backtest_ai_invalid_ai_output_returns_400(client):
    """Regression: Pydantic ValidationError from bad AI output must not become 500."""
    with patch(
        "services.ai.prompt_parser.PromptParser.parse_backtest_prompt",
        side_effect=PromptParserError("AI returned invalid backtest data"),
    ):
        response = client.post(
            "/api/v1/backtest/ai",
            json={"prompt": "backtest with invalid data"},
        )

    assert response.status_code == 400


def test_backtest_prompt_parser_handles_validation_error():
    """Invalid AI JSON fields must be converted to PromptParserError."""
    mock_service = MagicMock()
    mock_service.parse_backtest_prompts.return_value = [
        {
            "symbols": ["VCB"],
            "start_date": "2025-01-01",
            "end_date": "2024-01-01",
            "strategy": "buy_and_hold",
            "rebalance_frequency": "monthly",
            "initial_cash": 100000000,
        }
    ]

    parser = PromptParser()
    with patch(
        "services.ai.batch_ai.BatchAIService",
        return_value=mock_service,
    ):
        with pytest.raises(PromptParserError):
            parser.parse_backtest_prompt("invalid dates")
