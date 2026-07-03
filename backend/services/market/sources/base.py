import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from common.models import Asset


class Source(ABC):
    """Abstract market data source."""

    code: str
    name: str
    description: str
    supported_types: List[str]
    supports_history: bool = False
    supports_listing: bool = False

    @abstractmethod
    def fetch_price(self, asset: Asset) -> Optional[dict]:
        """Return {price, change, change_percent, date} or None."""
        pass

    def fetch_history(
        self,
        symbol: str,
        asset_type: str,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        """Return {date: close_price} mapping. Default empty."""
        return {}

    def fetch_listing(self) -> List[dict]:
        """Return list of {symbol, name, exchange, type}. Default empty."""
        return []


class SourceRegistry:
    """Registry of available market data sources."""

    def __init__(self):
        self._sources: Dict[str, Source] = {}

    def register(self, source: Source):
        self._sources[source.code] = source

    def get(self, code: str) -> Optional[Source]:
        return self._sources.get(code)

    def all(self) -> List[Source]:
        return list(self._sources.values())

    def for_type(self, asset_type: str) -> List[Source]:
        return [s for s in self._sources.values() if asset_type in s.supported_types]

    def supports_history(self, code: str) -> bool:
        source = self._sources.get(code)
        return source.supports_history if source else False

    def supports_listing(self, code: str) -> bool:
        source = self._sources.get(code)
        return source.supports_listing if source else False
