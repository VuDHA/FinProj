"""Shared prompt templates and JSON parsing helpers for AI insight services."""

import json
import re
from typing import Any, Dict, List, Optional

from services.ai_provider import AIProviderFactory
from services.ai_queue import AIQueueBusyError
from services.batch_ai import BatchAIError, BatchAIService


from services.ai_insights.base_prompt import master_prompt


DEFAULT_LANGUAGE = "vi"


class InsightGenerationError(Exception):
    """Raised when an AI insight cannot be generated."""

    pass


def extract_json(text: str) -> Optional[str]:
    """Find the first JSON object or array in a string."""
    text = text.strip()
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    start = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start == -1:
        return None
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


def parse_insight_response(text: str) -> Dict[str, Any]:
    """Parse a JSON response into an insight dict with fallback text fields."""
    json_text = extract_json(text)
    if json_text:
        try:
            data = json.loads(json_text)
            if isinstance(data, dict):
                return _normalize_insight(data)
        except json.JSONDecodeError:
            pass
    return _fallback_insight(text)


def _normalize_insight(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the insight dict contains expected fields."""
    overall = str(data.get("overall", data.get("summary", ""))).strip()
    details = str(data.get("details", data.get("detail", ""))).strip()
    suggestions = data.get("suggestions", data.get("actions", []))
    if not isinstance(suggestions, list):
        suggestions = []
    suggestions = [str(s).strip() for s in suggestions if str(s).strip()]
    if not overall and not details:
        return _fallback_insight(str(data))
    return {
        "overall": overall or "Tóm tắt",
        "details": details or "Không có chi tiết.",
        "suggestions": suggestions,
    }


def _fallback_insight(text: str) -> Dict[str, Any]:
    """When the model does not return valid JSON, treat the whole text as details."""
    return {
        "overall": "Phân tích AI",
        "details": text.strip() or "Không có nội dung từ mô hình.",
        "suggestions": [],
    }


def generate_insight(prompt: str, task_name: str = "ai_insight", max_tokens: int = 8192) -> Dict[str, Any]:
    """Generate an AI insight and return parsed fields.

    Raises:
        InsightGenerationError: if no provider is available or the request fails.
    """
    try:
        service = BatchAIService(batch_size=1)
        text = service.generate_insight(prompt, max_tokens=max_tokens, task_name=task_name)
    except AIQueueBusyError:
        raise
    except BatchAIError as e:
        raise InsightGenerationError(f"Không có mô hình AI khả dụng: {e}") from e
    except Exception as e:
        raise InsightGenerationError(f"Lỗi khi gọi AI: {e}") from e

    result = parse_insight_response(text)
    result["used_ollama"] = not _is_gemini_used()
    return result


def minify_dict(data: Any, keep_fields: List[str]) -> Any:
    """Return a copy of a dict/list with only the requested fields kept.

    Recursively filters dicts inside lists. Non-dict values are passed through.
    """
    if isinstance(data, dict):
        return {k: data[k] for k in keep_fields if k in data}
    if isinstance(data, list):
        return [minify_dict(item, keep_fields) for item in data]
    return data


def _is_gemini_used() -> bool:
    """Return True if the current primary provider is Gemini."""
    try:
        provider = AIProviderFactory.primary_provider()
        return provider is not None
    except Exception:
        return False


def format_currency(value) -> str:
    """Format a number as Vietnamese currency."""
    return f"{float(value):,.0f} VND"


def format_percent(value) -> str:
    """Format a number as a percentage."""
    return f"{float(value):.2f}%"


def base_prompt(data: str, role: str, context: str, language: str = DEFAULT_LANGUAGE) -> str:
    """Build a structured prompt that asks for concise JSON output."""
    if language == "vi":
        return (
            f"{master_prompt('vi')}\n\n"
            f"Vai trò: {role}.\n"
            f"Yêu cầu: {context}\n\n"
            f"Dữ liệu:\n{data}\n\n"
            "Trả về JSON duy nhất, không thêm nội dung khác:\n"
            '{"overall":"...","details":"...","suggestions":["...","..."]}\n'
            "JSON:"
        )
    return (
        f"{master_prompt('en')}\n\n"
        f"Role: {role}.\n"
        f"Task: {context}\n\n"
        f"Data:\n{data}\n\n"
        "Return only JSON, no other content:\n"
        '{"overall":"...","details":"...","suggestions":["...","..."]}\n'
        "JSON:"
    )


def format_items(items: List[Dict[str, Any]], fields: List[str]) -> str:
    """Format a list of dicts as a readable string."""
    lines = []
    for item in items:
        parts = []
        for field in fields:
            value = item.get(field)
            if value is not None:
                parts.append(f"{field}={value}")
        lines.append(" - " + ", ".join(parts))
    return "\n".join(lines)
