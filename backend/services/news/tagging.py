import re
import unicodedata
from typing import Dict, List, Optional

from common.config import settings
from services.ai.ai_insights.base_prompt import master_prompt
from services.ai.ollama_client import OllamaClient, OllamaClientError


class LocalTagger:
    """Generate article tags using a local Ollama LLM as fallback.

    Kept for Ollama fallback only. Gemini batch processing is preferred when
    AI_PROVIDER=gemini.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT,
        max_tags: int = settings.OLLAMA_MAX_TAGS,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tags = max_tags

    def _build_prompt(
        self, title: str, summary: str, language: str, context: Optional[str] = None
    ) -> str:
        context_block = ""
        if context:
            if language == "vi":
                context_block = f"Bối cảnh:\n{context}\n\n"
            else:
                context_block = f"Context:\n{context}\n\n"
        if language == "vi":
            return (
                f"{master_prompt(language)}\n\n"
                "Bạn là chuyên gia phân loại tin tức tài chính. "
                "Hãy đọc tiêu đề và tóm tắt, rồi trả về từ 3 đến 5 tag ngắn gọn, "
                "liên quan đến chứng khoán, tài chính hoặc kinh tế. "
                "Mỗi tag là 1-2 từ, viết thường, không dấu câu nhưng giữ nguyên dấu tiếng Việt, cách nhau bằng dấu phẩy. "
                "Tất cả tag phải bằng tiếng Việt có dấu (ví dụ: cổ phiếu, chứng khoán, lãi suất, ngân hàng), tuyệt đối không dùng tiếng Việt không dấu hoặc tiếng Anh.\n\n"
                f"{context_block}"
                f"Tiêu đề: {title}\n"
                f"Tóm tắt: {summary}\n\n"
                "Tags:"
            )
        return (
            f"{master_prompt(language)}\n\n"
            "You are a financial news classifier. Read the title and summary, "
            "then return 3-5 short tags related to finance, stocks, or the economy. "
            "Each tag is 1-2 words, lowercase, no punctuation, separated by commas. "
            "All tags must be in Vietnamese with diacritics (e.g., cổ phiếu, chứng khoán, lãi suất), never English.\n\n"
            f"{context_block}"
            f"Title: {title}\n"
            f"Summary: {summary}\n\n"
            "Tags:"
        )

    def _clean(self, raw: str) -> List[str]:
        """Turn a model response into a clean list of tags."""
        # Drop any surrounding explanations, bullets, or numbering
        cleaned = raw.strip()
        if "\n" in cleaned:
            cleaned = cleaned.split("\n")[0]

        tags = []
        for token in re.split(r"[,;|]", cleaned):
            token = unicodedata.normalize("NFC", token).strip().lower()
            token = re.sub(r"^[-\d\s]+", "", token)  # strip leading bullets/numbers
            token = re.sub(r"[-\d\s]+$", "", token)
            token = re.sub(r"[^\w\s]", "", token)
            if 1 < len(token) <= 24:
                tags.append(token)

        return tags[: self.max_tags]

    def generate(
        self, title: str, summary: str, language: str = "vi", context: Optional[str] = None
    ) -> List[str]:
        """Call the local Ollama model and return a list of tags."""
        prompt = self._build_prompt(title, summary, language, context=context)
        try:
            client = OllamaClient(base_url=self.base_url, timeout=self.timeout)
            raw = client.generate(
                prompt=prompt,
                model=self.model,
                options={
                    "temperature": 0.2,
                    "num_predict": 256,
                },
                task_name="news_tagging",
            )
            return self._clean(raw)
        except OllamaClientError as e:
            # Never fail the whole pipeline because of a tag call
            print(f"[news:tagger] ollama failed: {e}")
            return []


class KeywordTagger:
    """Rule-based fallback when the local LLM is unavailable."""

    _VIETNAMESE_KEYWORDS = {
        "chứng khoán": "chứng khoán",
        "cổ phiếu": "cổ phiếu",
        "lợi nhuận": "lợi nhuận",
        "doanh thu": "doanh thu",
        "lãi suất": "lãi suất",
        "tăng trưởng": "tăng trưởng",
        "thị trường": "thị trường",
        "ngân hàng": "ngân hàng",
        "bất động sản": "bất động sản",
        "dầu khí": "dầu khí",
        "xuất khẩu": "xuất khẩu",
        "nhập khẩu": "nhập khẩu",
        "fed": "fed",
        "vnindex": "vnindex",
    }

    _ENGLISH_KEYWORDS = {
        "stock": "stock market",
        "market": "stock market",
        "earnings": "earnings",
        "profit": "profit",
        "revenue": "revenue",
        "interest rate": "interest rate",
        "growth": "growth",
        "bank": "banking",
        "real estate": "real estate",
        "oil": "energy",
        "export": "trade",
        "import": "trade",
        "fed": "fed",
        "s&p": "s&p 500",
    }

    def generate(self, title: str, summary: str, language: str = "vi") -> List[str]:
        text = f"{title} {summary}".lower()
        keywords = self._VIETNAMESE_KEYWORDS if language == "vi" else self._ENGLISH_KEYWORDS
        tags = [tag for word, tag in keywords.items() if word in text]
        return tags[:5]


class TaggingService:
    """Unified entry point. Uses Gemini batch when configured, otherwise Ollama/keywords."""

    def __init__(self, context: Optional[str] = None, batch_size: int = settings.AI_BATCH_SIZE):
        self._llm = LocalTagger() if settings.OLLAMA_ENABLED else None
        self._fallback = KeywordTagger()
        self._context = context
        self._batch_size = batch_size

    def generate(self, article: Dict) -> List[str]:
        return self.generate_batch([article])[0]

    def generate_batch(self, articles: List[Dict]) -> List[List[str]]:
        if not articles:
            return []

        if settings.AI_PROVIDER == "gemini":
            try:
                from services.ai.batch_ai import BatchAIService

                service = BatchAIService(batch_size=self._batch_size)
                return service.generate_tags(
                    articles, language=articles[0].get("language", "vi"), context=self._context
                )
            except Exception as e:
                print(f"[tagging] batch service failed: {e}")

        # Fallback: process one by one
        results = []
        for article in articles:
            language = article.get("language", "vi")
            title = (article.get("title") or "").strip()
            summary = (article.get("summary") or "").strip()
            if not title and not summary:
                results.append([])
                continue

            tags = []
            if self._llm is not None:
                try:
                    tags = self._llm.generate(title, summary, language, context=self._context)
                except Exception as e:
                    print(f"[tagging] ollama failed: {e}")
            if not tags:
                tags = self._fallback.generate(title, summary, language)
            results.append(tags)
        return results

    def join(self, tags: List[str]) -> Optional[str]:
        """Return comma-separated tags for storage."""
        return ", ".join(tags) if tags else None
