"""Shared HTTP helpers for external API calls."""
from typing import Any, Dict, Optional

import requests


DEFAULT_USER_AGENT = "Mozilla/5.0"


def http_get(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10,
) -> requests.Response:
    merged_headers = {**{"User-Agent": DEFAULT_USER_AGENT}, **(headers or {})}
    return requests.get(url, params=params, headers=merged_headers, timeout=timeout)


def http_post(
    url: str,
    *,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10,
) -> requests.Response:
    merged_headers = {**{"Content-Type": "application/json"}, **(headers or {})}
    return requests.post(url, json=json, headers=merged_headers, timeout=timeout)
