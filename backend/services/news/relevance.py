import json
import re
from typing import Dict, List, Optional

from config import settings
from services.ai_insights.base_prompt import master_prompt
from services.ollama_client import OllamaClient


class RelevanceScorer:
    """Score how relevant a news article is to finance/investing.

    Uses Gemini batch when AI_PROVIDER=gemini; otherwise uses a local Ollama
    model when enabled. Falls back to a deterministic rule-based score when no
    AI provider is available.
    """

    def __init__(
        self,
        threshold: float = settings.NEWS_RELEVANCE_THRESHOLD,
        model: str = settings.OLLAMA_MODEL,
        base_url: str = settings.OLLAMA_BASE_URL,
        timeout: int = settings.OLLAMA_TIMEOUT,
        enabled: Optional[bool] = None,
    ):
        self.threshold = threshold
        self.model = model
        # Enabled when any AI provider is active: Gemini primary or Ollama enabled.
        self.enabled = enabled if enabled is not None else (
            settings.AI_PROVIDER == "gemini" or settings.OLLAMA_ENABLED
        )
        self._base_url = base_url
        self._timeout = timeout
        self._client: Optional[OllamaClient] = None

    def _get_client(self) -> OllamaClient:
        if self._client is None:
            self._client = OllamaClient(base_url=self._base_url, timeout=self._timeout)
        return self._client

    def score(self, article: Dict) -> Dict:
        """Return a dict with relevance_score, is_standout, and reason."""
        return self.score_batch([article])[0]

    def score_batch(self, articles: List[Dict]) -> List[Dict]:
        """Return a relevance score for each article."""
        if not articles:
            return []

        if settings.AI_PROVIDER == "gemini":
            try:
                from services.batch_ai import BatchAIService

                service = BatchAIService(batch_size=self._infer_batch_size())
                language = articles[0].get("language", "vi")
                return service.score_relevance(articles, language=language, threshold=self.threshold)
            except Exception as e:
                print(f"[news:relevance] batch service failed: {e}")
            return [self._rule_based_score(a) for a in articles]

        if self.enabled:
            return [self._llm_score(a) for a in articles]

        return [self._rule_based_score(a) for a in articles]

    def _infer_batch_size(self) -> int:
        return max(1, settings.AI_BATCH_SIZE)

    def _llm_score(self, article: Dict) -> Dict:
        region = article.get("region", "vn")
        language = article.get("language", "vi" if region == "vn" else "en")
        title = article.get("title", "")
        summary = article.get("summary", "")
        category = article.get("category", "")

        if language == "vi":
            prompt = (
                f"{master_prompt(language)}\n\n"
                "Bạn là chuyên gia tài chính. Hãy đánh giá mức độ liên quan của tin tức sau "
                "đối với nhà đầu tư Việt Nam (cổ phiếu, chứng khoán, ngân hàng, doanh nghiệp, "
                "kinh tế vĩ mô, thị trường tài chính).\n\n"
                f"Tiêu đề: {title}\n"
                f"Tóm tắt: {summary}\n"
                f"Chuyên mục: {category}\n\n"
                "Trả về JSON với các trường:\n"
                "- relevance_score: số thực từ 0.0 đến 1.0\n"
                "- standout: true nếu tin đáng chú ý và có giá trị cho nhà đầu tư, ngược lại false\n"
                "- reason: giải thích ngắn trong 1 câu\n\n"
                "JSON:"
            )
        else:
            prompt = (
                f"{master_prompt(language)}\n\n"
                "You are a finance expert. Evaluate how relevant the following article is "
                "to global investors (markets, stocks, central banks, macroeconomics, "
                "corporate earnings, commodities, bonds).\n\n"
                f"Title: {title}\n"
                f"Summary: {summary}\n"
                f"Category: {category}\n\n"
                "Return JSON with:\n"
                "- relevance_score: float from 0.0 to 1.0\n"
                "- standout: true if the article is notable and valuable to investors, otherwise false\n"
                "- reason: one-sentence explanation\n\n"
                "JSON:"
            )

        raw = self._client.generate(
            prompt=prompt,
            model=self.model,
            options={
                "temperature": 0.1,
                "num_predict": 128,
            },
            task_name="news_relevance_score",
        ).strip()

        return self._parse_llm_response(raw, article)

    def _parse_llm_response(self, raw: str, article: Dict) -> Dict:
        # Try to extract a JSON object if the model added extra text.
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid json from relevance model: {e}") from e

        score = float(data.get("relevance_score", 0.0))
        score = max(0.0, min(1.0, score))
        standout = data.get("standout", score >= self.threshold)
        if isinstance(standout, str):
            standout = standout.strip().lower() in ("true", "yes", "1")
        else:
            standout = bool(standout)
        return {
            "relevance_score": round(score, 2),
            "is_standout": standout,
            "reason": data.get("reason", ""),
        }

    def _rule_based_score(self, article: Dict) -> Dict:
        text = " ".join(
            filter(
                None,
                [
                    article.get("title", ""),
                    article.get("summary", ""),
                    article.get("content_text", ""),
                ],
            )
        ).lower()
        region = article.get("region", "vn")
        category = (article.get("category") or "").lower()

        vn_keywords = {
            "cổ phiếu", "chứng khoán", "thị trường", "ngân hàng", "doanh nghiệp",
            "lợi nhuận", "tài chính", "vn-index", "vnindex", "hose", "hnx", "upcom",
            "đầu tư", "tăng trưởng", "gdp", "lãi suất", "fed", "crypto", "bitcoin",
            "etf", "quỹ", "trái phiếu", "bất động sản", "xuất khẩu", "nhập khẩu",
            "kinh tế", "vĩ mô", "vi mô", "lạm phát", "thuế", "ngân sách",
        }
        global_keywords = {
            "market", "stock", "stocks", "equity", "equities", "earnings", "revenue",
            "federal reserve", "fed", "economy", "trade", "inflation", "oil", "bonds",
            "treasury", "yield", "etf", "crypto", "bitcoin", "s&p 500", "nasdaq",
            "dow jones", "commodities", "forex", "interest rate", "macro",
            "merger", "acquisition", "ipo", "dividend", "futures", "options",
        }
        keywords = vn_keywords if region == "vn" else global_keywords

        score = 0.1

        symbols = article.get("symbols", []) or []
        if symbols:
            score += min(0.2, 0.05 * len(symbols))

        impact = article.get("impact_score") or 0.0
        if impact > 0.5:
            score += 0.15
        elif impact > 0.3:
            score += 0.05

        sentiment = article.get("sentiment_score") or 0.0
        if abs(sentiment) > 0.25:
            score += 0.05

        keyword_hits = sum(1 for kw in keywords if kw in text)
        score += min(0.3, 0.05 * keyword_hits)

        relevant_categories = {
            "vn": ["tai-chinh-ngan-hang", "chung-khoan", "doanh-nghiep", "kinh-te-vi-mo"],
            "global": ["markets", "economics", "stocks", "currencies", "commodities"],
        }
        if category in relevant_categories.get(region, []):
            score += 0.1

        if len(text) > 100:
            score += 0.05

        score = min(1.0, score)
        return {
            "relevance_score": round(score, 2),
            "is_standout": score >= self.threshold,
            "reason": "rule-based fallback",
        }
