from services.news.sources.base import NewsSourceAdapter, NewsSourceRegistry
from services.news.sources.vn.cafef import CafeFNewsSource
from services.news.sources.intl.yahoo_finance import YahooFinanceNewsSource

registry = NewsSourceRegistry()
registry.register(CafeFNewsSource())
registry.register(YahooFinanceNewsSource())

__all__ = [
    "NewsSourceAdapter",
    "NewsSourceRegistry",
    "registry",
    "CafeFNewsSource",
    "YahooFinanceNewsSource",
]
