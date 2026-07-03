import json
from unittest.mock import MagicMock, patch

import pytest

import common.config
from services.ai.ai_provider import AIProviderFactory
from services.ai.batch_ai import BatchAIService
from services.ai.gemini_client import GeminiClient, GeminiClientError


@pytest.fixture
def mock_settings_gemini(monkeypatch):
    monkeypatch.setattr(common.config.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(common.config.settings, "GEMINI_BASE_URL", "https://test.example.com")
    monkeypatch.setattr(common.config.settings, "GEMINI_MODEL", "gemini-test")
    monkeypatch.setattr(common.config.settings, "GEMINI_EMBEDDING_MODEL", "text-embedding-test")
    monkeypatch.setattr(common.config.settings, "GEMINI_EMBEDDING_DIMENSION", 768)
    monkeypatch.setattr(common.config.settings, "AI_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(common.config.settings, "AI_BATCH_SIZE", 5)
    monkeypatch.setattr(common.config.settings, "OLLAMA_MODEL", "qwen2.5:1.5b")
    monkeypatch.setattr(common.config.settings, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setattr(common.config.settings, "OLLAMA_MAX_TAGS", 5)
    monkeypatch.setattr(common.config.settings, "NEWS_RELEVANCE_THRESHOLD", 0.6)
    monkeypatch.setattr(common.config.settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(common.config.settings, "OLLAMA_ENABLED", False)
    monkeypatch.setattr(
        "services.ai.gemini_client.GeminiClient._build_client", lambda self: MagicMock()
    )
    yield common.config.settings


def test_gemini_client_requires_api_key():
    with patch.object(common.config.settings, "GEMINI_API_KEY", ""):
        with pytest.raises(GeminiClientError):
            GeminiClient()


def test_gemini_client_generate(mock_settings_gemini):
    client = GeminiClient()
    fake_response = MagicMock()
    fake_response.text = "hello"
    with patch.object(
        client._client.models, "generate_content", return_value=fake_response
    ) as mock_generate:
        result = client.generate("prompt")
        assert result == "hello"
        mock_generate.assert_called_once()


def test_gemini_client_generate_error(mock_settings_gemini):
    client = GeminiClient()
    with patch.object(
        client._client.models, "generate_content", side_effect=Exception("boom")
    ):
        with pytest.raises(GeminiClientError):
            client.generate("prompt")


def test_gemini_client_embed(mock_settings_gemini):
    client = GeminiClient()
    response = MagicMock()
    response.values = None
    response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    with patch.object(
        client._client.models, "embed_content", return_value=response
    ) as mock_embed:
        result = client.embed_batch(["text"])
        assert result == [[0.1, 0.2, 0.3]]
        mock_embed.assert_called_once()


def test_batch_ai_extract_json():
    service = BatchAIService(batch_size=2)
    assert service._extract_json('```json\n{"a":1}\n```') == '{"a":1}'
    assert service._extract_json("[{\"a\":1}]") == "[{\"a\":1}]"
    assert service._extract_json("some text {\"a\":1} more") == "{\"a\":1}"
    assert service._extract_json("") is None


def test_batch_ai_parse_batch_response():
    service = BatchAIService(batch_size=2)
    assert service._parse_batch_response('[{"a":1},{"b":2}]') == [{"a": 1}, {"b": 2}]
    assert service._parse_batch_response('{"results": [{"a":1}]}') == [{"a": 1}]
    assert service._parse_batch_response("not json") == []


def test_batch_ai_clean_tags():
    service = BatchAIService(batch_size=2)
    assert service._clean_tags("tag a, tag b, tag c", 5) == ["tag a", "tag b", "tag c"]
    assert service._clean_tags(["Tag A", "tag B"], 5) == ["tag a", "tag b"]


def test_batch_ai_clean_relevance():
    service = BatchAIService(batch_size=2)
    result = service._clean_relevance({"relevance_score": 0.85, "standout": "true"}, 0.6)
    assert result["relevance_score"] == 0.85
    assert result["is_standout"] is True


def test_batch_ai_generate_tags_uses_gemini(mock_settings_gemini):
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", False):
            service = BatchAIService(batch_size=2)
            fake_response = MagicMock()
            fake_response.text = json.dumps(
                [{"tags": "cổ phiếu, chứng khoán, tăng trưởng"}, {"tags": "lợi nhuận, ngân hàng"}]
            )
            with patch.object(
                service._primary._client.models,
                "generate_content",
                return_value=fake_response,
            ):
                results = service.generate_tags(
                    [
                        {"title": "T1", "summary": "S1", "language": "vi"},
                        {"title": "T2", "summary": "S2", "language": "vi"},
                    ]
                )
                assert len(results) == 2
                assert results[0] == ["cổ phiếu", "chứng khoán", "tăng trưởng"]
                assert results[1] == ["lợi nhuận", "ngân hàng"]


def test_batch_ai_score_relevance_fallback_to_ollama():
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", True):
            service = BatchAIService(batch_size=2)
            # No Gemini configured in this branch because patch only set the strings
            with patch.object(service, "_is_gemini", return_value=False):
                with patch.object(
                    service._fallback,
                    "generate",
                    return_value=json.dumps(
                        {"relevance_score": 0.8, "standout": True, "reason": "good"}
                    ),
                ):
                    results = service.score_relevance(
                        [
                            {"title": "T1", "summary": "S1", "language": "vi"},
                            {"title": "T2", "summary": "S2", "language": "vi"},
                        ]
                    )
                    assert len(results) == 2
                    assert results[0]["relevance_score"] == 0.8


def test_ai_provider_factory_ollama_fallback():
    with patch.object(common.config.settings, "AI_PROVIDER", "ollama"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", False):
            assert AIProviderFactory.primary_provider() is None
            assert AIProviderFactory.fallback_provider() is None


def test_ai_provider_factory_gemini_primary():
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "GEMINI_API_KEY", "key"):
            with patch.object(common.config.settings, "GEMINI_BASE_URL", "https://test"):
                with patch.object(common.config.settings, "AI_TIMEOUT_SECONDS", 30):
                    with patch.object(
                        GeminiClient, "_build_client", lambda self: MagicMock()
                    ):
                        provider = AIProviderFactory.primary_provider()
                        assert provider is not None


def test_batch_ai_clean_summary_output_strips_json_wrapper():
    service = BatchAIService(batch_size=2)
    assert service._clean_summary_output('{"summary": "hello world"}') == "hello world"


def test_batch_ai_clean_summary_output_strips_code_fences():
    service = BatchAIService(batch_size=2)
    assert service._clean_summary_output("```markdown\nhello\n```") == "hello"


def test_batch_ai_summarize_includes_all_articles(mock_settings_gemini):
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", False):
            service = BatchAIService(batch_size=1)
            articles = [{"title": f"T{i}", "summary": f"S{i}"} for i in range(8)]
            with patch.object(service, "_generate_with_fallback", return_value="summary"):
                service.summarize(articles, language="vi")
                prompt = service._generate_with_fallback.call_args[0][0]
                for i in range(8):
                    assert f"T{i}" in prompt


def test_batch_ai_summarize_token_budgets(mock_settings_gemini):
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", False):
            gemini_service = BatchAIService(batch_size=1)
            with patch.object(gemini_service, "_generate_with_fallback", return_value="x"):
                gemini_service.summarize([{"title": "T", "summary": "S"}], language="vi")
                assert gemini_service._generate_with_fallback.call_args[1]["max_tokens"] == 8192

    with patch.object(common.config.settings, "AI_PROVIDER", "ollama"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", True):
            ollama_service = BatchAIService(batch_size=1)
            with patch.object(ollama_service, "_is_gemini", return_value=False):
                with patch.object(ollama_service, "_generate_with_fallback", return_value="x"):
                    ollama_service.summarize([{"title": "T", "summary": "S"}], language="vi")
                    assert ollama_service._generate_with_fallback.call_args[1]["max_tokens"] == 2048


def test_batch_ai_create_embeddings_uses_gemini(mock_settings_gemini):
    with patch.object(common.config.settings, "AI_PROVIDER", "gemini"):
        with patch.object(common.config.settings, "OLLAMA_ENABLED", False):
            service = BatchAIService(batch_size=2)
            response = MagicMock()
            response.values = None
            response.embeddings = [
                MagicMock(values=[0.1, 0.2]),
                MagicMock(values=[0.3, 0.4]),
            ]
            with patch.object(
                service._primary._client.models,
                "embed_content",
                return_value=response,
            ) as mock_embed:
                results = service.create_embeddings(["text 1", "text 2"])
                assert len(results) == 2
                assert results[0] == [0.1, 0.2]
                assert results[1] == [0.3, 0.4]
                mock_embed.assert_called_once()
