"""Contract abstractions for Interactive Brokers assets."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AssetClass = Literal["STK", "ETF", "FX", "FUT", "OPT"]


class ContractSpec(BaseModel):
    """Portable contract definition independent from IB objects."""

    symbol: str
    asset_class: AssetClass = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    expiry: str | None = None
    strike: float | None = None
    right: Literal["C", "P"] | None = None
    multiplier: str | None = None

    @property
    def normalized_symbol(self) -> str:
        return self.symbol.replace("/", "").upper()

    def to_ib_contract(self):
        """Create an ib_insync contract object from the spec."""

        try:
            from ib_insync import Forex, Future, Option, Stock
        except ImportError as exc:  # pragma: no cover - integration-only path
            raise RuntimeError("ib_insync is required for IBKR connectivity") from exc

        if self.asset_class in {"STK", "ETF"}:
            return Stock(self.symbol, self.exchange, self.currency)

        if self.asset_class == "FX":
            pair = self.normalized_symbol
            if len(pair) != 6:
                raise ValueError("FX symbol must be 6 chars, e.g. EURUSD")
            return Forex(pair)

        if self.asset_class == "FUT":
            if not self.expiry:
                raise ValueError("Futures contract requires expiry (YYYYMM)")
            return Future(
                symbol=self.symbol,
                lastTradeDateOrContractMonth=self.expiry,
                exchange=self.exchange,
                currency=self.currency,
            )

        if self.asset_class == "OPT":
            if not all([self.expiry, self.strike, self.right]):
                raise ValueError("Options contract requires expiry, strike, and right")
            return Option(
                symbol=self.symbol,
                lastTradeDateOrContractMonth=self.expiry,
                strike=float(self.strike),
                right=self.right,
                exchange=self.exchange,
                currency=self.currency,
                multiplier=self.multiplier,
            )

        raise ValueError(f"Unsupported asset class: {self.asset_class}")


class QualifiedContract(BaseModel):
    """Structured response for qualified contracts."""

    con_id: int = Field(default=0)
    symbol: str
    asset_class: AssetClass
    exchange: str
    currency: str
    local_symbol: str | None = None
