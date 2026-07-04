from services.news.sources.base import NewsSourceAdapter, NewsSourceRegistry
from services.news.sources.intl.bloomberg import BloombergNewsSource
from services.news.sources.intl.investing import InvestingNewsSource
from services.news.sources.intl.yahoo_finance import YahooFinanceNewsSource
from services.news.sources.vn.cafef import CafeFNewsSource
from services.news.sources.vn.thoibaotaichinhvietnam import ThoiBaoTaiChinhVietNamNewsSource
from services.news.sources.vn.vietstock import VietStockNewsSource

registry = NewsSourceRegistry()
registry.register(CafeFNewsSource())
registry.register(VietStockNewsSource())
registry.register(ThoiBaoTaiChinhVietNamNewsSource())
registry.register(BloombergNewsSource())
registry.register(YahooFinanceNewsSource())
registry.register(InvestingNewsSource())

__all__ = [
    "NewsSourceAdapter",
    "NewsSourceRegistry",
    "registry",
    "CafeFNewsSource",
    "VietStockNewsSource",
    "ThoiBaoTaiChinhVietNamNewsSource",
    "BloombergNewsSource",
    "YahooFinanceNewsSource",
    "InvestingNewsSource",
]
