import datetime
import json
import re
from typing import Dict

from pydantic import ValidationError

from config import settings
from schemas import BacktestRequest


class PromptParserError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""

    pass


class PromptParser:
    """Use Gemini or the local LLM to extract structured data from natural-language prompts."""

    def __init__(
        self,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = settings.OLLAMA_TIMEOUT,
    ):
        self.model = model
        self.timeout = timeout

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

        raw_symbols = data.get("symbols")
        if not isinstance(raw_symbols, list) or not raw_symbols:
            raise PromptParserError("AI did not extract any symbols from the prompt.")

        data["symbols"] = [
            str(s).strip().upper() for s in raw_symbols if s and str(s).strip()
        ]

        raw_allocations = data.get("allocations")
        if raw_allocations:
            if not isinstance(raw_allocations, dict):
                raise PromptParserError("AI returned allocations in an unexpected format.")
            data["allocations"] = {
                str(k).strip().upper(): float(v)
                for k, v in raw_allocations.items()
                if k and str(v).strip()
            }

        try:
            return BacktestRequest(**data)
        except ValidationError as e:
            raise PromptParserError(f"AI response did not match the backtest schema: {e}")

    def parse_stress_prompt(self, prompt: str, base: BacktestRequest) -> BacktestRequest:
        """Apply a stress/what-if scenario from a prompt to a base BacktestRequest."""
        today = datetime.date.today()
        default_start = (today - datetime.timedelta(days=365)).isoformat()
        default_end = today.isoformat()

        base_data = {
            "symbols": base.symbols or [],
            "start_date": base.start_date.isoformat() if base.start_date else default_start,
            "end_date": base.end_date.isoformat() if base.end_date else default_end,
            "strategy": base.strategy,
            "rebalance_frequency": base.rebalance_frequency,
            "initial_cash": base.initial_cash,
            "positions": [
                {
                    "symbol": p.symbol,
                    "price": p.price,
                    "quantity": p.quantity,
                    "ratio": p.ratio,
                }
                for p in (base.positions or [])
            ],
        }

        try:
            from services.batch_ai import BatchAIService

            service = BatchAIService(batch_size=1)
            data = service.parse_stress_prompts([prompt], base_data, language="vi")[0]
        except Exception as e:
            raise PromptParserError(f"AI service failed: {e}")

        if data is None:
            raise PromptParserError("AI service returned no data.")

        merged = base_data.copy()
        merged.update(data)
        merged["start_date"] = self._normalize_date(merged.get("start_date", default_start))
        merged["end_date"] = self._normalize_date(merged.get("end_date", default_end))

        if "symbols" in merged:
            raw_symbols = merged["symbols"]
            if not isinstance(raw_symbols, list):
                raise PromptParserError("AI returned symbols in an unexpected format.")
            merged["symbols"] = [
                str(s).strip().upper() for s in raw_symbols if s and str(s).strip()
            ]

        if merged.get("allocations"):
            raw_allocations = merged["allocations"]
            if not isinstance(raw_allocations, dict):
                raise PromptParserError("AI returned allocations in an unexpected format.")
            merged["allocations"] = {
                str(k).strip().upper(): float(v)
                for k, v in raw_allocations.items()
                if k and str(v).strip()
            }

        try:
            return BacktestRequest(**merged)
        except ValidationError as e:
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
