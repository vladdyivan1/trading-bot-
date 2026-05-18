"""Live trading adapter guarded by configuration."""

from __future__ import annotations

from broker.orders import OrderRequest
from config.settings import settings


class LiveTrader:
    """Thin live order adapter. Disabled unless explicitly enabled."""

    def __init__(self, ibkr_client: object) -> None:
        self.ibkr_client = ibkr_client

    def place_order(self, symbol: str, asset_class: str, order_request: OrderRequest, **kwargs: object) -> object:
        if not settings.live_trading_allowed:
            raise PermissionError("Live trading is disabled by default")
        return self.ibkr_client.place_order(symbol, asset_class, order_request, **kwargs)
