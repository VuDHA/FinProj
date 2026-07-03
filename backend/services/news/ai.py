import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple

from config import settings
from services.ollama_client import OllamaClient, OllamaClientError


class NewsAI:
    """Lightweight AI helper for news tasks via a local Ollama model.

    The model is kept outside the Python process, so the app only pays for an
    HTTP call.  Prompts are intentionally small to work well with tiny models
    like qwen2.5:1.5b.
    """

    _summary_cache: Dict[str, Tuple[float, str]] = {}
    _cache_ttl_seconds: float = 300.0

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT,
        enabled: Optional[bool] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        # Active when Gemini or Ollama is enabled.
        self.enabled = enabled if enabled is not None else (
            settings.AI_PROVIDER == "gemini" or settings.OLLAMA_ENABLED
        )
        self._client = OllamaClient(base_url=base_url, timeout=timeout)

    def _summary_cache_key(
        self, articles: List[Dict], language: str, rag_context: Optional[str] = None
    ) -> str:
        """Stable cache key for a given set of articles and context."""
        content = json.dumps(
            {
                "language": language,
                "articles": [
                    {"title": a.get("title"), "summary": a.get("summary")} for a in articles
                ],
                "rag_context": rag_context,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_cached_summary(self, key: str) -> Optional[str]:
        """Return a cached summary if it is still fresh."""
        entry = self._summary_cache.get(key)
        if entry is None:
            return None
        cached_at, summary = entry
        if time.time() - cached_at > self._cache_ttl_seconds:
            self._summary_cache.pop(key, None)
            return None
        return summary

    def _build_summary_prompt(
        self, context: str, language: str, rag_context: Optional[str] = None
    ) -> str:
        rag_block = ""
        if rag_context:
            if language == "vi":
                rag_block = f"Bối cảnh cá nhân:\n{rag_context}\n\n"
            else:
                rag_block = f"Personal context:\n{rag_context}\n\n"
        if language == "vi":
            return (
                "Bạn là trợ lý tài chính. Dưới đây là một số tin tức gần đây. "
                "Hãy tóm tắt ngắn gọn trong 3-5 gạch đầu dòng, chỉ nêu ý chính, "
                "không giải thích thêm.\n\n"
                f"{rag_block}"
                f"{context}\n\n"
                "Tóm tắt:"
            )
        return (
            "You are a financial assistant. Below are some recent news articles. "
            "Summarize them in 3-5 bullet points, main takeaways only, no extra commentary.\n\n"
            f"{rag_block}"
            f"{context}\n\n"
            "Summary:"
        )

    def _fallback_summary(self, articles: List[Dict], language: str) -> str:
        intro = (
            "Tóm tắt nhanh (không có Ollama):"
            if language == "vi"
            else "Quick summary (Ollama unavailable):"
        )
        bullets = "\n".join(f"- {a['title']}" for a in articles)
        return f"{intro}\n{bullets}"

    def summarize(
        self, articles: List[Dict], language: str = "vi", rag_context: Optional[str] = None
    ) -> str:
        """Return a short AI summary of the provided articles.

        Uses Gemini batch when configured, falling back to Ollama or a simple title list.
        Reuses a cached result for the same set of articles/context.
        """
        if not articles:
            return "Không có tin tức để tóm tắt." if language == "vi" else "No articles to summarize."

        cache_key = self._summary_cache_key(articles, language, rag_context)
        cached = self._get_cached_summary(cache_key)
        if cached is not None:
            print(f"[news:ai] returning cached summary ({len(articles)} articles)")
            return cached

        if not self.enabled:
            result = self._fallback_summary(articles, language)
            self._summary_cache[cache_key] = (time.time(), result)
            return result

        try:
            start = time.time()
            from services.batch_ai import BatchAIService

            service = BatchAIService(batch_size=1)
            result = service.summarize(articles, language=language, context=rag_context)
            print(f"[news:ai] summary generated in {time.time() - start:.2f}s")
            self._summary_cache[cache_key] = (time.time(), result)
            return result
        except Exception as e:
            print(f"[news:ai] ai failed: {e}")
            result = self._fallback_summary(articles, language)
            self._summary_cache[cache_key] = (time.time(), result)
            return result
