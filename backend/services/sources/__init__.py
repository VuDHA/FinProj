from services.sources.base import Source, SourceRegistry
from services.sources.stocks import CafefStockSource, KbsStockSource
from services.sources.funds import FmarketFundSource
from services.sources.gold import SjcGoldSource, VangTodayGoldSource
from services.sources.crypto import CoinGeckoCryptoSource
from services.sources.tcbs import TcbsSource
from services.sources.dnse import DnseSource
from services.sources.vcbf import VcbfFundSource

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
