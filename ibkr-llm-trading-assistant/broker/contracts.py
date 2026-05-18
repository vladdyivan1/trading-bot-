"""Contract qualification for multiple asset classes."""

from __future__ import annotations

from typing import Optional

from ib_insync import Contract, Forex, Future, Option, Stock

from schemas import AssetClass


def create_stock_contract(
    symbol: str,
    exchange: str = "SMART",
    currency: str = "USD",
    primary_exchange: Optional[str] = None,
) -> Stock:
    """Create stock or ETF contract."""
    contract = Stock(symbol, exchange, currency)
    if primary_exchange:
        contract.primaryExchange = primary_exchange
    return contract


def create_forex_contract(symbol: str, currency: str = "USD") -> Forex:
    """Create forex pair contract (e.g. EURUSD)."""
    if len(symbol) == 6:
        pair = symbol
    else:
        pair = symbol.replace("/", "").replace(".", "")
    return Forex(pair)


def create_future_contract(
    symbol: str,
    exchange: str,
    expiry: str,
    currency: str = "USD",
) -> Future:
    """Create futures contract (Phase 4 extension)."""
    return Future(symbol, expiry, exchange, currency=currency)


def create_option_contract(
    symbol: str,
    expiry: str,
    strike: float,
    right: str,
    exchange: str = "SMART",
    currency: str = "USD",
) -> Option:
    """Create options contract (Phase 4 extension)."""
    return Option(symbol, expiry, strike, right, exchange, currency=currency)


def create_contract(
    symbol: str,
    asset_class: AssetClass,
    exchange: str = "SMART",
    currency: str = "USD",
    **kwargs,
) -> Contract:
    """Factory for contracts by asset class."""
    if asset_class in (AssetClass.STK, AssetClass.ETF):
        return create_stock_contract(symbol, exchange, currency, kwargs.get("primary_exchange"))
    if asset_class == AssetClass.CASH:
        return create_forex_contract(symbol, currency)
    if asset_class == AssetClass.FUT:
        return create_future_contract(
            symbol, kwargs.get("exchange", exchange), kwargs["expiry"], currency
        )
    if asset_class == AssetClass.OPT:
        return create_option_contract(
            symbol,
            kwargs["expiry"],
            kwargs["strike"],
            kwargs["right"],
            exchange,
            currency,
        )
    raise ValueError(f"Unsupported asset class: {asset_class}")


TIMEFRAME_TO_BAR_SIZE = {
    "1 min": "1 min",
    "5 mins": "5 mins",
    "15 mins": "15 mins",
    "1 hour": "1 hour",
    "1 day": "1 day",
}

TIMEFRAME_TO_DURATION = {
    "1 min": "1 D",
    "5 mins": "1 W",
    "15 mins": "2 W",
    "1 hour": "1 M",
    "1 day": "5 Y",
}
