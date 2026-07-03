import datetime
import json
import re
from typing import Any, Dict, List, Optional

from config import settings
from services.ai_provider import AIProviderError, AIProviderFactory
from services.gemini_client import GeminiClient, GeminiClientError
from services.ollama_client import OllamaClient, OllamaClientError


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

    def _generate_gemini(self, prompt: str, max_tokens: int, task_name: str) -> str:
        if not self._is_gemini():
            raise BatchAIError("Gemini is not configured")
        return self._primary.generate_batch(prompt, max_tokens=max_tokens, task_name=task_name)

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
    ) -> str:
        if self._is_gemini():
            try:
                return self._generate_gemini(prompt, max_tokens, task_name)
            except (GeminiClientError, BatchAIError) as e:
                print(f"[batch_ai] gemini failed for {task_name}: {e}")
        if self._fallback is not None:
            return self._generate_fallback(prompt, max_tokens, task_name)
        raise BatchAIError(f"No AI provider available for {task_name}")

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
        # Try bare JSON object or array
        match = re.search(r"([\{\[].*[\}\]])", text, re.DOTALL)
        if match:
            return match.group(1)
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
            "Bạn là chuyên gia phân loại tin tức tài chính. "
            "Với mỗi tin bên dưới, trả về 3-5 tag ngắn gọn liên quan đến tài chính/chứng khoán. "
            "Mỗi tag 1-2 từ, viết thường, không dấu câu, cách nhau bằng dấu phẩy. "
            "Tất cả tag bằng tiếng Việt.\n\n"
            if language == "vi"
            else "You are a financial news classifier. For each article below, return 3-5 short tags related to finance/stocks. Each tag is 1-2 words, lowercase, no punctuation, separated by commas.\n\n"
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
                    max_tokens=128,
                    task_name=task_name,
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_tags(
                            entry.get("tags", ""), max_tags
                        )
            except Exception as e:
                print(f"[batch_ai] tag batch failed: {e}")
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
                "Bạn là chuyên gia phân loại tin tức tài chính. "
                "Hãy đọc tiêu đề và tóm tắt, rồi trả về từ 3 đến 5 tag ngắn gọn, "
                "liên quan đến chứng khoán, tài chính hoặc kinh tế. "
                "Mỗi tag là 1-2 từ, viết thường, không dấu câu, cách nhau bằng dấu phẩy. "
                "Tất cả tag phải bằng tiếng Việt.\n\n"
                f"{context_block}"
                f"Tiêu đề: {title}\n"
                f"Tóm tắt: {summary}\n\n"
                "Tags:"
            )
        else:
            prompt = (
                "You are a financial news classifier. Read the title and summary, "
                "then return 3-5 short tags related to finance, stocks, or the economy. "
                "Each tag is 1-2 words, lowercase, no punctuation, separated by commas.\n\n"
                f"{context_block}"
                f"Title: {title}\n"
                f"Summary: {summary}\n\n"
                "Tags:"
            )
        try:
            raw = self._fallback.generate(
                prompt=prompt,
                model=settings.OLLAMA_MODEL,
                options={"temperature": 0.2, "num_predict": 128},
                task_name="ollama_tag_fallback",
            )
            return self._clean_tags(raw, max_tags)
        except Exception as e:
            print(f"[batch_ai] single tag fallback failed: {e}")
            return []

    def score_relevance(
        self,
        items: List[Dict[str, Any]],
        language: str = "vi",
        threshold: float = settings.NEWS_RELEVANCE_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        """Return a relevance score dict for each article."""
        if not items:
            return []

        task_name = "batch_relevance"
        instructions = (
            "Bạn là chuyên gia đánh giá tin tức tài chính. Với mỗi tin bên dưới, trả về:\n"
            "- relevance_score: số thực từ 0.0 đến 1.0\n"
            "- standout: true nếu tin đáng chú ý cho nhà đầu tư\n"
            "- reason: giải thích ngắn trong 1 câu\n\n"
            if language == "vi"
            else "You are a financial news evaluator. For each article below, return:\n"
            "- relevance_score: float from 0.0 to 1.0\n"
            "- standout: true if the article is notable for investors\n"
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
                    max_tokens=256,
                    task_name=task_name,
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_relevance(entry, threshold)
            except Exception as e:
                print(f"[batch_ai] relevance batch failed: {e}")
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
                options={"temperature": 0.1, "num_predict": 128},
                task_name="ollama_relevance_fallback",
            )
            entry = self._parse_single_json(raw) or {}
            return self._clean_relevance(entry, threshold)
        except Exception as e:
            print(f"[batch_ai] single relevance fallback failed: {e}")
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

        article_lines = "\n".join(
            f"{i + 1}. {a.get('title', '')}"
            + (f" - {a.get('summary', '')[:200]}" if a.get("summary") else "")
            for i, a in enumerate(items[:5])
        )

        prompt = (
            "Bạn là trợ lý tài chính. Dưới đây là một số tin tức gần đây. "
            "Hãy tóm tắt ngắn gọn trong 3-5 gạch đầu dòng, chỉ nêu ý chính.\n\n"
            if language == "vi"
            else "You are a financial assistant. Summarize the recent news below in 3-5 bullet points, main takeaways only.\n\n"
        )
        prompt += f"{context_block}{article_lines}\n\nTóm tắt:"

        try:
            return self._generate_with_fallback(
                prompt,
                max_tokens=256,
                task_name="batch_summary",
            ).strip()
        except Exception as e:
            print(f"[batch_ai] summary failed: {e}")
            return "Không có tin tức để tóm tắt." if language == "vi" else "No articles to summarize."

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
            "Bạn là trợ lý tài chính. Với mỗi danh sách tiêu đề cột, trả về JSON object "
            "với key là tiêu đề gốc và value là trường đích. "
            "Nếu không khớp, dùng null.\n\n"
            if language == "vi"
            else "You are a financial assistant. For each list of column headers, return a JSON object mapping original header to target field. Use null if no match.\n\n"
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
                    max_tokens=256,
                    task_name="batch_smart_import",
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_mapping(
                            entry, batch[i], target_fields
                        )
            except Exception as e:
                print(f"[batch_ai] mapping batch failed: {e}")
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
                options={"temperature": 0.1, "num_predict": 256},
                task_name="ollama_mapping_fallback",
            )
            entry = self._parse_single_json(raw) or {}
            return self._clean_mapping(entry, headers, target_fields)
        except Exception as e:
            print(f"[batch_ai] single mapping fallback failed: {e}")
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
            "Bạn là trợ lý tài chính. Với mỗi yêu cầu backtest, trả về JSON object với:\n"
            "- symbols: mảng ticker\n"
            "- start_date: YYYY-MM-DD\n"
            "- end_date: YYYY-MM-DD\n"
            "- strategy: 'buy_and_hold' hoặc 'rebalancing'\n"
            "- rebalance_frequency: 'monthly' hoặc 'quarterly'\n"
            "- initial_cash: số\n"
            "- allocations: object {ticker: phần trăm}\n\n"
            if language == "vi"
            else "You are a financial assistant. For each backtest prompt, return a JSON object with:\n"
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
                    max_tokens=512,
                    task_name="batch_backtest_parser",
                )
                parsed = self._parse_batch_response(raw)
                for i, entry in enumerate(parsed):
                    if i < len(batch):
                        results[batch_start + i] = self._clean_backtest(entry)
            except Exception as e:
                print(f"[batch_ai] backtest batch failed: {e}")
                for i, user_prompt in enumerate(batch):
                    results[batch_start + i] = self._parse_backtest_single(
                        user_prompt, language
                    )

        return results

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
                options={"temperature": 0.1, "num_predict": 256},
                task_name="ollama_backtest_fallback",
            )
            data = self._parse_single_json(raw) or {}
            data = self._clean_backtest(data)
            data["start_date"] = self._normalize_date(data.get("start_date", default_start))
            data["end_date"] = self._normalize_date(data.get("end_date", default_end))
            return data
        except Exception as e:
            print(f"[batch_ai] single backtest fallback failed: {e}")
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
                print(f"[batch_ai] gemini embed batch failed: {e}")

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
                except Exception as e:
                    print(f"[batch_ai] ollama embed fallback failed: {e}")
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
        json_text = BatchAIService._extract_json(raw)
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
            token = token.strip().lower()
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
        standout = entry.get("standout", score >= threshold)
        if isinstance(standout, str):
            standout = standout.strip().lower() in ("true", "yes", "1")
        else:
            standout = bool(standout)
        return {
            "relevance_score": round(score, 2),
            "is_standout": standout,
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
