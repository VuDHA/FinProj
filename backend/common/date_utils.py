"""Shared date/time and numeric parsing helpers."""
import datetime
from typing import Union


Value = Union[str, int, float, None]


def today() -> datetime.date:
    return datetime.datetime.now().date()


def parse_float(value: Value) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def parse_number(s: str) -> float:
    """Parse a number that may use commas as thousands separators."""
    if s is None:
        return 0.0
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def parse_date(value) -> datetime.date:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    try:
        return datetime.datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return today()


def parse_timestamp_date(ms: int) -> datetime.date:
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).date()
    except Exception:
        return today()
