from services.news.sources.base import NewsSourceAdapter, NewsSourceRegistry
from services.news.sources.vn.cafef import CafeFNewsSource
from services.news.sources.intl.bloomberg import BloombergNewsSource

registry = NewsSourceRegistry()
registry.register(CafeFNewsSource())
registry.register(BloombergNewsSource())

__all__ = [
    "NewsSourceAdapter",
    "NewsSourceRegistry",
    "registry",
    "CafeFNewsSource",
    "BloombergNewsSource",
]
