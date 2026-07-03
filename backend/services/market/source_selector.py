import datetime
from typing import Dict, List, Optional

from sqlmodel import Session

from common.models import Asset
from services.market.source_config import DEFAULT_SOURCES
from services.market.sources import registry
from services.market.sources.base import Source


class SourceSelector:
    """Resolves and executes the right data source for an asset."""

    def __init__(self, session: Session):
        self.session = session
        self._default_sources: Optional[Dict[str, str]] = None

    def _get_defaults(self) -> Dict[str, str]:
        if self._default_sources is None:
            from services.market.source_config import get_default_sources

            self._default_sources = get_default_sources(self.session)
        return self._default_sources

    def _sources_for_type(self, asset_type: str) -> List[Source]:
        return registry.for_type(asset_type)

    def _resolve_source(self, asset: Asset) -> Optional[Source]:
        preferred = self._resolve_asset_source(asset)
        sources = self._sources_for_type(asset.type)
        by_code = {s.code: s for s in sources}
        if preferred in by_code:
            return by_code[preferred]
        # Fallback to first available source if preferred is invalid.
        return sources[0] if sources else None

    def _resolve_asset_source(self, asset: Asset) -> str:
        """Return effective source code for an asset using cached defaults."""
        if asset.source:
            source = registry.get(asset.source)
            if source and asset.type in source.supported_types:
                return asset.source
        defaults = self._get_defaults()
        return defaults.get(asset.type, DEFAULT_SOURCES.get(asset.type, "kbs"))

    def fetch_price(self, asset: Asset) -> tuple[Optional[dict], List[str]]:
        """Return (price_data, warnings). Tries preferred source first, then fallbacks."""
        warnings: List[str] = []
        preferred_code = self._resolve_asset_source(asset)
        sources = self._sources_for_type(asset.type)
        by_code = {s.code: s for s in sources}

        ordered = []
        if preferred_code in by_code:
            ordered.append(by_code[preferred_code])
        for s in sources:
            if s not in ordered:
                ordered.append(s)

        for source in ordered:
            try:
                data = source.fetch_price(asset)
                if data and data.get("price", 0) > 0:
                    if source.code != preferred_code and preferred_code in by_code:
                        warnings.append(
                            f"Nguồn đã chọn {preferred_code} không khả dụng; đã dùng {source.code}."
                        )
                    return data, warnings
            except Exception as e:
                warnings.append(f"Lỗi khi lấy giá từ {source.code}: {e}")
        if not ordered:
            warnings.append(f"Không có nguồn nào hỗ trợ loại tài sản {asset.type}.")
        return None, warnings

    def fetch_history(
        self,
        asset: Asset,
        start: datetime.date,
        end: datetime.date,
    ) -> Dict[datetime.date, float]:
        preferred_code = self._resolve_asset_source(asset)
        sources = self._sources_for_type(asset.type)
        by_code = {s.code: s for s in sources}

        ordered = []
        if preferred_code in by_code:
            ordered.append(by_code[preferred_code])
        for s in sources:
            if s not in ordered:
                ordered.append(s)

        for source in ordered:
            try:
                data = source.fetch_history(asset.symbol, asset.type, start, end)
                if data:
                    return data
            except Exception as e:
                print(f"[source_selector] history {asset.symbol} via {source.code} error: {e}")
        return {}

    def fetch_listing(self, asset_type: str) -> List[dict]:
        listings = []
        seen = set()
        for source in self._sources_for_type(asset_type):
            try:
                for item in source.fetch_listing():
                    symbol = item.get("symbol", "").upper()
                    item_type = item.get("type", asset_type).upper()
                    key = (symbol, item_type)
                    if key in seen:
                        continue
                    seen.add(key)
                    listings.append(item)
            except Exception:
                continue
        return listings
