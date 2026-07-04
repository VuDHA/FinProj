BUY_TYPES = {"BUY", "DEPOSIT"}
SELL_TYPES = {"SELL", "WITHDRAWAL"}
MARKET_TRANSACTION_TYPES = {"BUY", "SELL"}
NON_MARKET_TRANSACTION_TYPES = {"BUY", "SELL", "DEPOSIT", "WITHDRAWAL"}


def is_buy_type(transaction_type: str) -> bool:
    return transaction_type in BUY_TYPES


def is_sell_type(transaction_type: str) -> bool:
    return transaction_type in SELL_TYPES
