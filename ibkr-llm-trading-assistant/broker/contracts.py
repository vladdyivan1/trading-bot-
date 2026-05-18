"""Contract qualification helpers for IBKR asset classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ib_insync import Contract, Forex, Future, Option, Stock

if TYPE_CHECKING:
    from ib_insync import IB


def stock_contract(
    symbol: str,
    exchange: str = "SMART",
    currency: str = "USD",
    primary_exchange: str | None = None,
) -> Stock:
    """Build a stock/ETF contract."""
    c = Stock(symbol, exchange, currency)
    if primary_exchange:
        c.primaryExchange = primary_exchange
    return c


def forex_contract(symbol: str, exchange: str = "IDEALPRO") -> Forex:
    """Build a forex pair contract (e.g. EURUSD)."""
    if len(symbol) == 6:
        return Forex(symbol[:3], exchange, symbol[3:])
    return Forex(symbol, exchange)


def future_contract(
    symbol: str,
    exchange: str,
    expiry: str,
    currency: str = "USD",
) -> Future:
    """Build a futures contract (Phase 4)."""
    return Future(symbol, exchange, expiry, currency=currency)


def option_contract(
    symbol: str,
    expiry: str,
    strike: float,
    right: str,
    exchange: str = "SMART",
    currency: str = "USD",
) -> Option:
    """Build an options contract (Phase 4)."""
    return Option(symbol, expiry, strike, right.upper(), exchange, currency=currency)


def build_contract(
    symbol: str,
    asset_class: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    **kwargs,
) -> Contract:
    """Factory for contracts by asset class."""
    asset_class = asset_class.upper()
    if asset_class in ("STK", "ETF"):
        return stock_contract(symbol, exchange, currency, kwargs.get("primary_exchange"))
    if asset_class == "CASH":
        return forex_contract(symbol, kwargs.get("exchange", "IDEALPRO"))
    if asset_class == "FUT":
        return future_contract(
            symbol,
            exchange,
            kwargs["expiry"],
            currency,
        )
    if asset_class == "OPT":
        return option_contract(
            symbol,
            kwargs["expiry"],
            kwargs["strike"],
            kwargs.get("right", "C"),
            exchange,
            currency,
        )
    raise ValueError(f"Unsupported asset class: {asset_class}")


async def qualify_contract(ib: IB, contract: Contract) -> Contract:
    """Qualify a contract with IBKR."""
    qualified = await ib.qualifyContractsAsync(contract)
    if not qualified:
        raise ValueError(f"Could not qualify contract: {contract}")
    return qualified[0]
