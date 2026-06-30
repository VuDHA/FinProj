import time
from typing import Dict, List, Optional

from config import settings
from services.ollama_client import OllamaClient, OllamaClientError


class NewsAI:
    """Lightweight AI helper for news tasks via a local Ollama model.

    The model is kept outside the Python process, so the app only pays for an
    HTTP call.  Prompts are intentionally small to work well with tiny models
    like qwen2.5:1.5b.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT,
        enabled: bool = settings.OLLAMA_ENABLED,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.enabled = enabled
        self._client = OllamaClient(base_url=base_url, timeout=timeout)

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

        Falls back to a simple title list when Ollama is disabled or fails.
        """
        if not articles:
            return "Không có tin tức để tóm tắt." if language == "vi" else "No articles to summarize."

        # Keep the context small for tiny models: titles + truncated summaries
        context = "\n".join(
            f"{i + 1}. {a['title']}"
            + (f" - {a['summary'][:200]}" if a.get("summary") else "")
            for i, a in enumerate(articles[:5])
        )

        if not self.enabled:
            return self._fallback_summary(articles, language)

        try:
            start = time.time()
            raw = self._client.generate(
                prompt=self._build_summary_prompt(context, language, rag_context=rag_context),
                model=self.model,
                options={
                    "temperature": 0.3,
                    "num_predict": 256,
                },
                task_name="news_summary",
            ).strip()
            print(f"[news:ai] summary generated in {time.time() - start:.2f}s")
            if not raw:
                return self._fallback_summary(articles, language)
            return raw
        except OllamaClientError as e:
            print(f"[news:ai] ollama failed: {e}")
            return self._fallback_summary(articles, language)
