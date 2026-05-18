"""IBKR contract factory helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

try:
    from ib_insync import Contract, Forex, Future, Option, Stock
except ImportError:  # pragma: no cover - exercised only without optional dependency
    Contract = object  # type: ignore[assignment]
    Forex = Future = Option = Stock = None  # type: ignore[assignment]


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    asset_class: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    last_trade_date_or_contract_month: str | None = None
    strike: float | None = None
    right: str | None = None
    multiplier: str | None = None


def build_contract(spec: ContractSpec) -> Contract:
    """Create an ib_insync contract for supported asset classes."""

    if Stock is None:
        raise RuntimeError("ib_insync is required for IBKR contract creation")

    asset_class = spec.asset_class.upper()
    if asset_class in {"STK", "ETF"}:
        return Stock(spec.symbol, spec.exchange, spec.currency)
    if asset_class == "CASH":
        pair = spec.symbol if "." not in spec.symbol else spec.symbol.replace(".", "")
        if len(pair) == 6:
            return Forex(pair)
        return Forex(f"{spec.symbol}{spec.currency}")
    if asset_class == "FUT":
        if not spec.last_trade_date_or_contract_month:
            raise ValueError("Futures require last_trade_date_or_contract_month")
        return Future(
            spec.symbol,
            spec.last_trade_date_or_contract_month,
            exchange=spec.exchange,
            currency=spec.currency,
            multiplier=spec.multiplier,
        )
    if asset_class == "OPT":
        if not spec.last_trade_date_or_contract_month or spec.strike is None or not spec.right:
            raise ValueError("Options require expiry, strike, and right")
        return Option(
            spec.symbol,
            spec.last_trade_date_or_contract_month,
            spec.strike,
            spec.right.upper(),
            exchange=spec.exchange,
            currency=spec.currency,
            multiplier=spec.multiplier,
        )
    raise ValueError(f"Unsupported asset class: {spec.asset_class}")


def option_expiry(value: date) -> str:
    """Format an option expiry for IBKR."""

    return value.strftime("%Y%m%d")
