"""Live market data helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketQuote:
    symbol: str
    bid: float | None
    ask: float | None
    last: float | None

    @property
    def mid(self) -> float | None:
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last

    @property
    def spread_pct(self) -> float | None:
        if self.bid is None or self.ask is None or self.mid in (None, 0):
            return None
        return (self.ask - self.bid) / self.mid


class MarketDataService:
    """Wrapper for real-time quote retrieval."""

    def __init__(self, ibkr_client: object) -> None:
        self.ibkr_client = ibkr_client

    def quote(self, symbol: str, asset_class: str = "STK", exchange: str = "SMART", currency: str = "USD") -> MarketQuote:
        get_quote = getattr(self.ibkr_client, "get_quote")
        return get_quote(symbol=symbol, asset_class=asset_class, exchange=exchange, currency=currency)
