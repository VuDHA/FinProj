import datetime
import json
import re
from typing import Dict

from config import settings
from schemas import BacktestRequest
from services.ollama_client import OllamaClient, OllamaClientError


class PromptParserError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""

    pass


class PromptParser:
    """Use the local LLM to extract structured data from natural-language prompts."""

    def __init__(
        self,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT,
    ):
        self.model = model
        self.timeout = timeout
        self._client = OllamaClient(timeout=timeout)

    def _parse_json(self, raw: str) -> Dict:
        """Extract a JSON object from a possibly chatty LLM response."""
        # If the response contains a fenced code block, use its content.
        code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if code_block:
            raw = code_block.group(1)
        else:
            # Otherwise look for the first JSON object.
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                raw = match.group(0)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise PromptParserError(f"AI response is not valid JSON: {e}")

    def parse_backtest_prompt(self, prompt: str) -> BacktestRequest:
        """Convert a natural-language backtest prompt into a BacktestRequest."""
        today = datetime.date.today()
        default_start = (today - datetime.timedelta(days=365)).isoformat()
        default_end = today.isoformat()

        try:
            from services.batch_ai import BatchAIService

            service = BatchAIService(batch_size=1)
            data = service.parse_backtest_prompts([prompt], language="vi")[0]
        except Exception as e:
            raise PromptParserError(f"AI service failed: {e}")

        if data is None:
            raise PromptParserError("AI service returned no data.")

        # Normalize dates if the LLM returned relative terms or non-ISO formats.
        data["start_date"] = self._normalize_date(data.get("start_date", default_start))
        data["end_date"] = self._normalize_date(data.get("end_date", default_end))

        if "symbols" not in data or not data["symbols"]:
            raise PromptParserError("AI did not extract any symbols from the prompt.")

        data["symbols"] = [s.strip().upper() for s in data["symbols"] if s and s.strip()]

        if data.get("allocations"):
            data["allocations"] = {
                k.strip().upper(): float(v)
                for k, v in data["allocations"].items()
                if k and str(v).strip()
            }

        try:
            return BacktestRequest(**data)
        except ValueError as e:
            raise PromptParserError(f"AI response did not match the backtest schema: {e}")

    def _normalize_date(self, value) -> str:
        """Return an ISO date string from various LLM outputs."""
        if isinstance(value, datetime.date):
            return value.isoformat()
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        # Try common formats
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue
        # If the string already looks like ISO, return it.
        if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return value
        raise PromptParserError(f"Could not parse date: {value}")
