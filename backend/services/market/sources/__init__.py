from services.market.sources.base import Source, SourceRegistry
from services.market.sources.stocks import CafefStockSource, KbsStockSource
from services.market.sources.funds import FmarketFundSource
from services.market.sources.gold import SjcGoldSource, VangTodayGoldSource
from services.market.sources.crypto import CoinGeckoCryptoSource
from services.market.sources.tcbs import TcbsSource
from services.market.sources.dnse import DnseSource
from services.market.sources.vcbf import VcbfFundSource

registry = SourceRegistry()
registry.register(KbsStockSource())
registry.register(CafefStockSource())
registry.register(FmarketFundSource())
registry.register(VangTodayGoldSource())
registry.register(SjcGoldSource())
registry.register(CoinGeckoCryptoSource())
registry.register(TcbsSource())
registry.register(DnseSource())
registry.register(VcbfFundSource())

__all__ = [
    "Source",
    "SourceRegistry",
    "registry",
    "KbsStockSource",
    "CafefStockSource",
    "FmarketFundSource",
    "VangTodayGoldSource",
    "SjcGoldSource",
    "CoinGeckoCryptoSource",
    "TcbsSource",
    "DnseSource",
    "VcbfFundSource",
]
