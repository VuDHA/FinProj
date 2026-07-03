"""Shared JSON parsing helpers."""
import json
import re
from typing import Any, Dict, Optional


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


def safe_loads(text: str) -> Optional[Any]:
    """Safely parse JSON, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def parse_single_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse the first JSON object from a string."""
    json_text = extract_json(text)
    if json_text is None:
        return None
    data = safe_loads(json_text)
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data:
        return data[0]
    return None
