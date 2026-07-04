import datetime
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

from config import settings
from services.ai_insights.base_prompt import master_prompt
from services.ai_provider import AIProviderFactory
from services.gemini_client import GeminiClient, GeminiClientError
from services.ollama_client import OllamaClient


# Longer summaries give the AI more context. Gemini models support large context
# windows, so we keep this high rather than the previous 300-char default.
DEFAULT_NEWS_SUMMARY_MAX_LENGTH = 4000


class BatchAIError(Exception):
    """Raised when no AI provider can handle a batch request."""

    pass


class BatchAIService:
    """Dispatch AI tasks in batches to Gemini, falling back to Ollama per item.

    Each public method accepts a list of tasks, builds a batched prompt for the
    primary provider, and parses the JSON response. If the batch fails or any item
    is malformed, it retries the failed items individually with the fallback provider.
    """

    def __init__(self, batch_size: int = settings.AI_BATCH_SIZE):
        self.batch_size = max(1, batch_size)
        self._primary = None
        self._fallback = None
        self._init_providers()

    def _init_providers(self) -> None:
        try:
            self._primary = AIProviderFactory.primary_provider()
        except Exception:
            self._primary = None
        try:
            self._fallback = AIProviderFactory.fallback_provider()
        except Exception:
            self._fallback = None

    def _is_gemini(self) -> bool:
        return self._primary is not None and isinstance(self._primary, GeminiClient)

    def _generate_gemini(
        self,
        prompt: str,
        max_tokens: int,
        task_name: str,
        response_mime_type: str = "application/json",
    ) -> str:
        if not self._is_gemini():
            raise BatchAIError("Gemini is not configured")
        return self._primary.generate_batch(
            prompt,
            max_tokens=max_tokens,
            task_name=task_name,
            response_mime_type=response_mime_type,
        )

    def _generate_fallback(self, prompt: str, max_tokens: int, task_name: str) -> str:
        if self._fallback is None:
            raise BatchAIError("No fallback AI provider configured")
        return self._fallback.generate(
            prompt=prompt,
            model=settings.OLLAMA_MODEL,
            options={
                "temperature": 0.2,
                "num_predict": max_tokens,
            },
            task_name=task_name,
        )

    def _generate_with_fallback(
        self,
        prompt: str,
        max_tokens: int,
        task_name: str,
        response_mime_type: str = "application/json",
    ) -> str:
        if self._is_gemini():
            try:
                return self._generate_gemini(
                    prompt, max_tokens, task_name, response_mime_type=response_mime_type
                )
            except (GeminiClientError, BatchAIError) as e:
                pass
        if self._fallback is not None:
            return self._generate_fallback(prompt, max_tokens, task_name)
        raise BatchAIError(f"No AI provider available for {task_name}")

    def generate_insight(
        self,
        prompt: str,
        max_tokens: int = 8192,
        task_name: str = "ai_insight",
    ) -> str:
        """Generate a single AI insight with provider fallback.

        Returns raw text. The caller is responsible for parsing any structured
        JSON from the response.
        """
        return self._generate_with_fallback(prompt, max_tokens, task_name)

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Find the first JSON object or array in a string."""
        text = text.strip()
        if not text:
            return None
        # Try fenced code block
        match = re.search(r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        # Try bare JSON object or array, from the first { or [ to the matching end.
        start = -1
        for i, ch in enumerate(text):
            if ch in "{[":
                start = i
                break
        if start == -1:
            return None
        # Count braces/brackets to find the matching end.
        open_char = text[start]
        close_char = "}" if open_char == "{" else "]"
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        return None

    def _parse_single_json(self, text: str) -> Optional[Dict[str, Any]]:
        json_text = self._extract_json(text)
        if json_text is None:
            return None
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data:
            return data[0]
        return None

    def generate_tags(
        self,
        items: List[Dict[str, Any]],
        language: str = "vi",
        context: Optional[str] = None,
    ) -> List[List[str]]:
        """Return a list of tags for each article."""
        if not items:
            return []

        task_name = "batch_tags"
        max_tags = settings.OLLAMA_MAX_TAGS
        context_block = ""
        if context:
            context_block = f"Bối cảnh:\n{context}\n\n" if language == "vi" else f"Context:\n{context}\n\n"

        instructions = (
            f"{master_prompt(language)}\n\n"
            "Bạn là chuyên gia phân loại tin tức tài chính. "
            "Với mỗi tin bên dưới, trả về 3-5 tag ngắn gọn liên quan đến tài chính/chứng khoán. "
            "Mỗi tag 1-2 từ, viết thường, không dấu câu nhưng giữ nguyên dấu tiếng Việt, cách nhau bằng dấu phẩy. "
            "Tất cả tag bằng tiếng Việt có dấu (ví dụ: cổ phiếu, chứng khoán, lãi suất), tuyệt đối không dùng tiếng Việt không dấu hoặc tiếng Anh.\n\n"
            if language == "vi"
            else f"{master_prompt(language)}\n\n"
            "You are a financial news classifier. For each article below, return 3-5 short tags related to finance/stocks. Each tag is 1-2 words, lowercase, no punctuation, separated by commas. All tags must be in Vietnamese with diacritics (e.g., cổ phiếu, chứng khoán, lãi suất), never English.\n\n"
        )

        results: List[Optional[List[str]]] = [None] * len(items)
        for batch_start in range(0, len(items), self.batch_size):
            batch = items[batch_start : batch_start + self.batch_size]
            batch_prompt = self._build_batch_prompt(
                instructions,
                context_block,
                batch,
                "title",
                "summary",
                language,
                "tags",
            )
            try:
                raw = self._generate_with_fallback(
                    batch_prompt,
                    max_tokens=2048,
                    task_name=task_name,
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_tags(
                            entry.get("tags", ""), max_tags
                        )
            except Exception as e:
                # Fall back per item
                for i, item in enumerate(batch):
                    results[batch_start + i] = self._generate_tags_single(
                        item, language, context, max_tags
                    )

        return [r if r is not None else [] for r in results]

    def _generate_tags_single(
        self,
        item: Dict[str, Any],
        language: str,
        context: Optional[str],
        max_tags: int,
    ) -> List[str]:
        if self._fallback is None:
            return []
        title = item.get("title", "")
        summary = item.get("summary", "")
        context_block = ""
        if context:
            context_block = f"Bối cảnh:\n{context}\n\n" if language == "vi" else f"Context:\n{context}\n\n"
        if language == "vi":
            prompt = (
                f"{master_prompt(language)}\n\n"
                "Bạn là chuyên gia phân loại tin tức tài chính. "
                "Hãy đọc tiêu đề và tóm tắt, rồi trả về từ 3 đến 5 tag ngắn gọn, "
                "liên quan đến chứng khoán, tài chính hoặc kinh tế. "
                "Mỗi tag là 1-2 từ, viết thường, không dấu câu nhưng giữ nguyên dấu tiếng Việt, cách nhau bằng dấu phẩy. "
                "Tất cả tag phải bằng tiếng Việt có dấu (ví dụ: cổ phiếu, chứng khoán, lãi suất), tuyệt đối không dùng tiếng Việt không dấu hoặc tiếng Anh.\n\n"
                f"{context_block}"
                f"Tiêu đề: {title}\n"
                f"Tóm tắt: {summary}\n\n"
                "Tags:"
            )
        else:
            prompt = (
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
        try:
            raw = self._fallback.generate(
                prompt=prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.2, "num_predict": 256},
                task_name="ollama_tag_fallback",
            )
            return self._clean_tags(raw, max_tags)
        except Exception as e:
            return []

    def score_relevance(
        self,
        items: List[Dict[str, Any]],
        language: str = "vi",
        threshold: float = settings.NEWS_RELEVANCE_THRESHOLD,
        region: str = "vn",
    ) -> List[Dict[str, Any]]:
        """Return a relevance score dict for each article."""
        if not items:
            return []

        task_name = "batch_relevance"
        if language == "vi" or region == "vn":
            instructions = (
                f"{master_prompt(language)}\n\n"
                "Bạn là chuyên gia phân tích tin tức tài chính. Với mỗi tin bên dưới, "
                "đánh giá mức độ liên quan đến nhà đầu tư tại Việt Nam (cổ phiếu, chứng khoán, "
                "ngân hàng, doanh nghiệp niêm yết, kinh tế vĩ mô, lãi suất, tỷ giá, hàng hóa, "
                "trái phiếu, tiền tệ). Tin từ các nguồn uy tín về thị trường Việt Nam là rất liên quan.\n"
                "Thang điểm:\n"
                "- 0.8–1.0: tin lớn ảnh hưởng toàn thị trường (Fed, lãi suất, KQKD lớn, khủng hoảng)\n"
                "- 0.6–0.79: tin đáng chú ý cho nhà đầu tư (doanh nghiệp, ngành, kinh tế vĩ mô)\n"
                "- 0.4–0.59: tin liên quan nhẹ, không đủ nổi bật\n"
                "- 0.0–0.39: tin ít liên quan hoặc không liên quan đến đầu tư\n"
                "Trả về:\n"
                "- relevance_score: số thực từ 0.0 đến 1.0\n"
                "- standout: true nếu tin quan trọng và đáng chú ý cho nhà đầu tư, ngược lại false\n"
                "- reason: giải thích ngắn trong 1 câu\n\n"
            )
        else:
            instructions = (
                f"{master_prompt(language)}\n\n"
                "You are a financial analyst. For each article below, evaluate relevance to investing "
                "(stocks, banking, macroeconomics, corporate earnings, global markets, commodities, bonds, currencies). "
                "News from Bloomberg, Reuters, CNBC, Financial Times about markets is highly relevant.\n"
                "Scale:\n"
                "- 0.8–1.0: major market-moving news (Fed, rates, big earnings, crises)\n"
                "- 0.6–0.79: notable for investors (companies, sectors, macro)\n"
                "- 0.4–0.59: lightly related, not standout\n"
                "- 0.0–0.39: little or no investment relevance\n"
                "Return:\n"
                "- relevance_score: float from 0.0 to 1.0\n"
                "- standout: true if the article is notable and valuable to investors, otherwise false\n"
                "- reason: one-sentence explanation\n\n"
            )

        results: List[Optional[Dict[str, Any]]] = [None] * len(items)
        for batch_start in range(0, len(items), self.batch_size):
            batch = items[batch_start : batch_start + self.batch_size]
            batch_prompt = self._build_batch_prompt(
                instructions,
                "",
                batch,
                "title",
                "summary",
                language,
                "relevance",
                extra_fields={"category": "category", "symbols": "symbols"},
            )
            try:
                raw = self._generate_with_fallback(
                    batch_prompt,
                    max_tokens=4096,
                    task_name=task_name,
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        cleaned = self._clean_relevance(entry, threshold)
                        title = batch[i].get("title", "")[:60]
                        #     f"[relevance] {title!r} score={cleaned['relevance_score']} "
                        #     f"standout={cleaned['is_standout']} reason={cleaned['reason'][:60]}"
                        # )
                        results[batch_start + i] = cleaned
            except Exception as e:
                for i, item in enumerate(batch):
                    results[batch_start + i] = self._score_relevance_single(
                        item, language, threshold
                    )

        return [r if r is not None else self._default_relevance(threshold) for r in results]

    def _score_relevance_single(
        self,
        item: Dict[str, Any],
        language: str,
        threshold: float,
    ) -> Dict[str, Any]:
        if self._fallback is None:
            return self._default_relevance(threshold)
        title = item.get("title", "")
        summary = item.get("summary", "")
        category = item.get("category", "")
        if language == "vi":
            prompt = (
                f"{master_prompt(language)}\n\n"
                "Bạn là chuyên gia tài chính. Đánh giá mức độ liên quan của tin tức sau đối với nhà đầu tư.\n\n"
                f"Tiêu đề: {title}\n"
                f"Tóm tắt: {summary}\n"
                f"Chuyên mục: {category}\n\n"
                "Trả về JSON với các trường:\n"
                "- relevance_score: số thực từ 0.0 đến 1.0\n"
                "- standout: true nếu tin đáng chú ý\n"
                "- reason: giải thích ngắn\n\n"
                "JSON:"
            )
        else:
            prompt = (
                f"{master_prompt(language)}\n\n"
                "You are a finance expert. Evaluate how relevant this article is to investors.\n\n"
                f"Title: {title}\n"
                f"Summary: {summary}\n"
                f"Category: {category}\n\n"
                "Return JSON with:\n"
                "- relevance_score: float from 0.0 to 1.0\n"
                "- standout: true if notable\n"
                "- reason: short explanation\n\n"
                "JSON:"
            )
        try:
            raw = self._fallback.generate(
                prompt=prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.1, "num_predict": 256},
                task_name="ollama_relevance_fallback",
            )
            entry = self._parse_single_json(raw) or {}
            cleaned = self._clean_relevance(entry, threshold)
            #     f"[relevance:fallback] {title[:60]!r} score={cleaned['relevance_score']} "
            #     f"standout={cleaned['is_standout']}"
            # )
            return cleaned
        except Exception as e:
            return self._default_relevance(threshold)

    def summarize(
        self,
        items: List[Dict[str, Any]],
        language: str = "vi",
        context: Optional[str] = None,
    ) -> str:
        """Return a single summary string for a list of articles."""
        if not items:
            return "Không có tin tức để tóm tắt." if language == "vi" else "No articles to summarize."

        context_block = ""
        if context:
            context_block = f"Bối cảnh cá nhân:\n{context}\n\n" if language == "vi" else f"Personal context:\n{context}\n\n"

        def _article_line(i: int, a: Dict[str, Any]) -> str:
            title = a.get("title") or ""
            summary = a.get("summary") or ""
            published = a.get("published_at") or ""
            url = a.get("url") or ""
            tags = a.get("tags") or ""
            symbols = a.get("symbols") or []
            impact = a.get("impact_score")
            parts = [f"{i + 1}. Tiêu đề: {title}"]
            if published:
                parts.append(f"   Ngày: {published}")
            if summary:
                parts.append(f"   Tóm tắt: {summary[:DEFAULT_NEWS_SUMMARY_MAX_LENGTH]}")
            if tags:
                parts.append(f"   Chủ đề: {tags}")
            if symbols:
                parts.append(f"   Mã CK: {', '.join(str(s) for s in symbols)}")
            if impact is not None:
                parts.append(f"   Mức độ tác động: {impact:.0%}")
            if url:
                parts.append(f"   Nguồn: {url}")
            return "\n".join(parts)

        article_lines = "\n\n".join(
            _article_line(i, a)
            for i, a in enumerate(items)
            if a.get("title") or a.get("summary")
        )

        if language == "vi":
            prompt = (
                f"{master_prompt(language)}\n\n"
                "Bạn là biên tập viên tài chính cao cấp. Dựa trên toàn bộ các tin tức được cung cấp (theo thứ tự mới nhất đến cũ), "
                "hãy viết một bài tổng hợp thị trường toàn diện, dễ đọc, bằng tiếng Việt. "
                "Trả về nội dung định dạng Markdown với tiêu đề, đoạn văn và gạch đầu dòng. "
                "KHÔNG trả về JSON, KHÔNG bọc trong {summary: ...}. "
                "Nội dung cần:\n"
                "- Một đoạn mở đầu tổng quan thị trường\n"
                "- Các yếu tố chính đang tác động đến thị trường\n"
                "- Tác động đến nhóm ngành/cổ phiếu quan trọng\n"
                "- Ý nghĩa cho nhà đầu tư\n"
                "- Nếu có bối cảnh cá nhân, hãy đề cập các mã người dùng đang quan tâm\n"
                "- Cuối cùng liệt kê 3-5 nguồn tin chính kèm ngày và URL\n\n"
            )
        else:
            prompt = (
                f"{master_prompt(language)}\n\n"
                "You are a senior financial editor. Based on all the provided news (latest to oldest), "
                "write a comprehensive, readable market summary. "
                "Return Markdown with headings, paragraphs, and bullet points. "
                "DO NOT return JSON or wrap the output in {summary: ...}. "
                "Cover: market overview, key drivers, sector/stock impact, investment implications, personalized context, "
                "and end with 3-5 key sources with dates and URLs.\n\n"
            )
        prompt += f"{context_block}{article_lines}\n\nTóm tắt:"

        # Gemini output is capped at 8192; news summary gets 4x for Ollama.
        max_tokens = 8192 if self._is_gemini() else 2048

        try:
            raw = self._generate_with_fallback(
                prompt,
                max_tokens=max_tokens,
                task_name="batch_summary",
                response_mime_type="text/plain",
            ).strip()
            return self._clean_summary_output(raw)
        except Exception as e:
            return "Không có tin tức để tóm tắt." if language == "vi" else "No articles to summarize."

    @staticmethod
    def _clean_summary_output(raw: str) -> str:
        """Strip accidental JSON wrappers and code fences from the summary."""
        text = raw.strip()
        # Remove outer JSON object if the model wrapped the summary.
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "summary" in data:
                    text = str(data["summary"])
            except json.JSONDecodeError:
                pass
        # Remove markdown code fences if present.
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def suggest_mappings(
        self,
        headers_list: List[List[str]],
        import_type: str,
        language: str = "vi",
    ) -> List[Dict[str, Optional[str]]]:
        """Return a header mapping for each list of headers."""
        if not headers_list:
            return []

        target_fields = (
            ["symbol", "name", "type", "exchange", "currency"]
            if import_type == "assets"
            else ["symbol", "type", "quantity", "price", "fee", "date", "notes"]
        )

        instructions = (
            f"{master_prompt(language)}\n\n"
            "Bạn là trợ lý tài chính. Với mỗi danh sách tiêu đề cột, trả về JSON object "
            "với key là tiêu đề gốc và value là trường đích. "
            "Nếu không khớp, dùng null.\n\n"
            if language == "vi"
            else f"{master_prompt(language)}\n\n"
            "You are a financial assistant. For each list of column headers, return a JSON object mapping original header to target field. Use null if no match.\n\n"
        )

        results: List[Optional[Dict[str, Optional[str]]]] = [None] * len(headers_list)
        for batch_start in range(0, len(headers_list), self.batch_size):
            batch = headers_list[batch_start : batch_start + self.batch_size]
            prompt = instructions
            prompt += f"Import type: {import_type}\nTarget fields: {', '.join(target_fields)}\n\n"
            for i, headers in enumerate(batch):
                prompt += f"{i + 1}. Headers: {', '.join(headers)}\n"
            prompt += "\nReturn a JSON array of objects, one per list:\nJSON:"

            try:
                raw = self._generate_with_fallback(
                    prompt,
                    max_tokens=512,
                    task_name="batch_smart_import",
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_mapping(
                            entry, batch[i], target_fields
                        )
            except Exception as e:
                for i, headers in enumerate(batch):
                    results[batch_start + i] = self._suggest_mapping_single(
                        headers, import_type, language
                    )

        return [
            r if r is not None else {h: None for h in headers_list[i]}
            for i, r in enumerate(results)
        ]

    def _suggest_mapping_single(
        self,
        headers: List[str],
        import_type: str,
        language: str,
    ) -> Dict[str, Optional[str]]:
        if self._fallback is None:
            return {h: None for h in headers}
        target_fields = (
            ["symbol", "name", "type", "exchange", "currency"]
            if import_type == "assets"
            else ["symbol", "type", "quantity", "price", "fee", "date", "notes"]
        )
        if language == "vi":
            prompt = (
                f"{master_prompt(language)}\n\n"
                "Bạn là trợ lý tài chính. Ánh xạ mỗi tiêu đề cột sang trường đích phù hợp. "
                "Trả về JSON object duy nhất với key là tiêu đề gốc và value là trường đích. "
                "Nếu không khớp, dùng null.\n\n"
                f"Loại import: {import_type}\n"
                f"Trường đích: {', '.join(target_fields)}\n"
                f"Tiêu đề: {', '.join(headers)}\n\n"
                "JSON:"
            )
        else:
            prompt = (
                f"{master_prompt(language)}\n\n"
                "You are a financial assistant. Map each source column header to a target field. "
                "Return a single JSON object where keys are original headers and values are target fields. "
                "Use null if no match.\n\n"
                f"Import type: {import_type}\n"
                f"Target fields: {', '.join(target_fields)}\n"
                f"Headers: {', '.join(headers)}\n\n"
                "JSON:"
            )
        try:
            raw = self._fallback.generate(
                prompt=prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.1, "num_predict": 512},
                task_name="ollama_mapping_fallback",
            )
            entry = self._parse_single_json(raw) or {}
            return self._clean_mapping(entry, headers, target_fields)
        except Exception as e:
            return {h: None for h in headers}

    def parse_backtest_prompts(
        self,
        prompts: List[str],
        language: str = "vi",
    ) -> List[Optional[Dict[str, Any]]]:
        """Return parsed backtest request dicts for each prompt."""
        if not prompts:
            return []

        instructions = (
            f"{master_prompt(language)}\n\n"
            "Bạn là trợ lý tài chính. Với mỗi yêu cầu backtest, trả về JSON object với:\n"
            "- symbols: mảng ticker\n"
            "- start_date: YYYY-MM-DD\n"
            "- end_date: YYYY-MM-DD\n"
            "- strategy: 'buy_and_hold' hoặc 'rebalancing'\n"
            "- rebalance_frequency: 'monthly' hoặc 'quarterly'\n"
            "- initial_cash: số\n"
            "- allocations: object {ticker: phần trăm}\n\n"
            if language == "vi"
            else f"{master_prompt(language)}\n\n"
            "You are a financial assistant. For each backtest prompt, return a JSON object with:\n"
            "- symbols: array of tickers\n"
            "- start_date: YYYY-MM-DD\n"
            "- end_date: YYYY-MM-DD\n"
            "- strategy: 'buy_and_hold' or 'rebalancing'\n"
            "- rebalance_frequency: 'monthly' or 'quarterly'\n"
            "- initial_cash: number\n"
            "- allocations: object {ticker: percentage}\n\n"
        )

        results: List[Optional[Dict[str, Any]]] = [None] * len(prompts)
        for batch_start in range(0, len(prompts), self.batch_size):
            batch = prompts[batch_start : batch_start + self.batch_size]
            prompt = instructions
            for i, user_prompt in enumerate(batch):
                prompt += f"{i + 1}. {user_prompt}\n"
            prompt += "\nReturn a JSON array of objects, one per prompt:\nJSON:"

            try:
                raw = self._generate_with_fallback(
                    prompt,
                    max_tokens=1024,
                    task_name="batch_backtest_parser",
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_backtest(entry)
            except Exception as e:
                for i, user_prompt in enumerate(batch):
                    results[batch_start + i] = self._parse_backtest_single(
                        user_prompt, language
                    )

        return results

    def parse_stress_prompts(
        self,
        prompts: List[str],
        base_request: Dict[str, Any],
        language: str = "vi",
    ) -> List[Optional[Dict[str, Any]]]:
        """Return parsed stress/what-if backtest modifications for each prompt."""
        if not prompts:
            return []

        base_json = json.dumps(base_request, ensure_ascii=False, default=str)
        instructions = (
            f"{master_prompt(language)}\n\n"
            "Bạn là trợ lý tài chính. Người dùng đang mô tả một kịch bản stress/what-if cho backtest. "
            "Dựa trên yêu cầu backtest hiện tại (base), trả về JSON object chỉ chứa các trường CẦN THAY ĐỔI. "
            "Có thể thay đổi: symbols, start_date, end_date, strategy, rebalance_frequency, "
            "initial_cash, allocations, positions.\n\n"
            f"Base request:\n{base_json}\n\n"
            if language == "vi"
            else f"{master_prompt(language)}\n\n"
            "You are a financial assistant. The user is describing a stress/what-if scenario for a backtest. "
            "Based on the current base request, return a JSON object containing ONLY the fields that should change. "
            "You may change: symbols, start_date, end_date, strategy, rebalance_frequency, "
            "initial_cash, allocations, positions.\n\n"
            f"Base request:\n{base_json}\n\n"
        )

        results: List[Optional[Dict[str, Any]]] = [None] * len(prompts)
        for batch_start in range(0, len(prompts), self.batch_size):
            batch = prompts[batch_start : batch_start + self.batch_size]
            prompt = instructions
            for i, user_prompt in enumerate(batch):
                prompt += f"{i + 1}. {user_prompt}\n"
            prompt += "\nReturn a JSON array of objects, one per prompt:\nJSON:"

            try:
                raw = self._generate_with_fallback(
                    prompt,
                    max_tokens=4096,
                    task_name="batch_stress_parser",
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_backtest(entry)
            except Exception as e:
                for i, user_prompt in enumerate(batch):
                    results[batch_start + i] = self._parse_stress_single(
                        user_prompt, base_request, language
                    )

        return results

    def _parse_stress_single(
        self,
        user_prompt: str,
        base_request: Dict[str, Any],
        language: str,
    ) -> Optional[Dict[str, Any]]:
        if self._fallback is None:
            return None
        system_prompt = (
            f"{master_prompt('en')}\n\n"
            "You are a financial assistant. The user describes a stress/what-if scenario for a backtest. "
            "Return only a JSON object with the fields that should change from the base request. "
            "You may change: symbols, start_date, end_date, strategy, rebalance_frequency, "
            "initial_cash, allocations, positions.\n\n"
            f"Base request:\n{json.dumps(base_request, ensure_ascii=False, default=str)}\n\n"
            f"User prompt: {user_prompt}\n\n"
            "JSON:"
        )
        try:
            raw = self._fallback.generate(
                prompt=system_prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.1, "num_predict": 512},
                task_name="ollama_stress_fallback",
            )
            data = self._parse_single_json(raw) or {}
            return self._clean_backtest(data)
        except Exception as e:
            return None

    def _parse_backtest_single(
        self,
        user_prompt: str,
        language: str,
    ) -> Optional[Dict[str, Any]]:
        if self._fallback is None:
            return None
        today = datetime.date.today()
        default_start = (today - datetime.timedelta(days=365)).isoformat()
        default_end = today.isoformat()
        system_prompt = (
            f"{master_prompt('en')}\n\n"
            "You are a financial assistant. Extract a JSON object for a portfolio backtest "
            "from the user's Vietnamese or English prompt. Use ISO dates (YYYY-MM-DD). "
            "Use only 'buy_and_hold' or 'rebalancing' as strategy. "
            "Use only 'monthly' or 'quarterly' as rebalance_frequency. "
            "Return only the JSON object, no commentary.\n\n"
            "JSON schema:\n"
            "{\n"
            '  "symbols": ["VCB", "VNM"],\n'
            '  "start_date": "2023-01-01",\n'
            '  "end_date": "2023-12-31",\n'
            '  "strategy": "rebalancing",\n'
            '  "rebalance_frequency": "monthly",\n'
            '  "initial_cash": 100000000,\n'
            '  "allocations": {"VCB": 40, "VNM": 60}\n'
            "}\n\n"
            f"User prompt: {user_prompt}\n\n"
            "JSON:"
        )
        try:
            raw = self._fallback.generate(
                prompt=system_prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.1, "num_predict": 512},
                task_name="ollama_backtest_fallback",
            )
            data = self._parse_single_json(raw) or {}
            data = self._clean_backtest(data)
            data["start_date"] = self._normalize_date(data.get("start_date", default_start))
            data["end_date"] = self._normalize_date(data.get("end_date", default_end))
            return data
        except Exception as e:
            return None

    @staticmethod
    def _normalize_date(value) -> str:
        if isinstance(value, datetime.date):
            return value.isoformat()
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return value
        raise ValueError(f"Could not parse date: {value}")

    def create_embeddings(
        self,
        texts: List[str],
    ) -> List[Optional[List[float]]]:
        """Return embedding vectors for each text."""
        if not texts:
            return []

        # Prefer Gemini for batched embeddings.
        if self._is_gemini():
            try:
                batch_size = 10
                vectors: List[Optional[List[float]]] = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    batch_vectors = self._primary.embed_batch(
                        batch,
                        task_name="batch_embed",
                    )
                    vectors.extend(batch_vectors)
                return vectors
            except Exception as e:
                pass

        # Fallback to Ollama per text.
        if self._fallback is not None:
            results: List[Optional[List[float]]] = []
            for text in texts:
                try:
                    results.append(
                        self._fallback.embed(
                            text=text,
                            model=settings.OLLAMA_EMBEDDING_MODEL,
                            task_name="ollama_embed_fallback",
                        )
                    )
                except Exception:
                    results.append(None)
            return results

        return [None] * len(texts)

    # --- prompt building helpers ---

    @staticmethod
    def _build_batch_prompt(
        instructions: str,
        context_block: str,
        items: List[Dict[str, Any]],
        title_key: str,
        summary_key: str,
        language: str,
        task_type: str,
        extra_fields: Optional[Dict[str, str]] = None,
        max_summary_length: int = DEFAULT_NEWS_SUMMARY_MAX_LENGTH,
    ) -> str:
        prompt = instructions
        if context_block:
            prompt += context_block
        prompt += (
            "Dưới đây là các tin:\n\n"
            if language == "vi"
            else "Here are the articles:\n\n"
        )
        for i, item in enumerate(items):
            prompt += f"{i + 1}. Title: {item.get(title_key, '')}\n"
            summary = item.get(summary_key, "")
            if summary:
                if len(summary) > max_summary_length:
                    summary = summary[:max_summary_length].rsplit(" ", 1)[0] + "..."
                prompt += f"   Summary: {summary}\n"
            if extra_fields:
                for key, label in extra_fields.items():
                    value = item.get(key)
                    if value:
                        prompt += f"   {label}: {value}\n"
            prompt += "\n"

        if task_type == "tags":
            prompt += (
                "Return a JSON array of objects, one per article. Each object has a 'tags' field with comma-separated tags.\nJSON:"
            )
        elif task_type == "relevance":
            prompt += (
                "Return a JSON array of objects, one per article. Each object has 'relevance_score', 'standout', and 'reason'.\nJSON:"
            )
        else:
            prompt += "Return a JSON array of objects, one per item.\nJSON:"
        return prompt

    @staticmethod
    def _parse_batch_response(raw: str) -> List[Dict[str, Any]]:
        # Try direct parse first.
        text = raw.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_text = BatchAIService._extract_json(text)
            if json_text is None:
                return []
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                return []
        if isinstance(data, dict):
            # Sometimes the model wraps the array under a key like "results"
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]
        if isinstance(data, list):
            return data
        return []

    @staticmethod
    def _clean_tags(raw: Any, max_tags: int) -> List[str]:
        if isinstance(raw, list):
            text = ", ".join(str(t) for t in raw)
        else:
            text = str(raw or "")
        tags = []
        for token in re.split(r"[,;|]", text):
            token = unicodedata.normalize("NFC", token).strip().lower()
            token = re.sub(r"^[-\d\s]+", "", token)
            token = re.sub(r"[-\d\s]+$", "", token)
            token = re.sub(r"[^\w\s]", "", token)
            if 1 < len(token) <= 24:
                tags.append(token)
        return tags[:max_tags]

    @staticmethod
    def _clean_relevance(entry: Dict[str, Any], threshold: float) -> Dict[str, Any]:
        score = float(entry.get("relevance_score", 0.0))
        score = max(0.0, min(1.0, score))
        standout = entry.get("standout", False)
        if isinstance(standout, str):
            standout = standout.strip().lower() in ("true", "yes", "1")
        else:
            standout = bool(standout)
        # Prioritize relevance score: a high score is enough to be standout.
        is_standout = standout or score >= threshold
        return {
            "relevance_score": round(score, 2),
            "is_standout": is_standout,
            "reason": str(entry.get("reason", "")),
        }

    @staticmethod
    def _default_relevance(threshold: float) -> Dict[str, Any]:
        return {
            "relevance_score": 0.0,
            "is_standout": False,
            "reason": "",
        }

    @staticmethod
    def _clean_mapping(
        entry: Dict[str, Any],
        headers: List[str],
        target_fields: List[str],
    ) -> Dict[str, Optional[str]]:
        cleaned: Dict[str, Optional[str]] = {}
        for header in headers:
            value = entry.get(header)
            if value not in target_fields:
                value = None
            cleaned[header] = value
        return cleaned

    @staticmethod
    def _clean_backtest(entry: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(entry)
        if data.get("symbols"):
            data["symbols"] = [
                s.strip().upper() for s in data["symbols"] if s and str(s).strip()
            ]
        if data.get("allocations"):
            data["allocations"] = {
                k.strip().upper(): float(v)
                for k, v in data["allocations"].items()
                if k and str(v).strip()
            }
        return data
