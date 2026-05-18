"""Paper trading execution adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from broker.orders import OrderRequest


@dataclass
class PaperFill:
    order_id: str
    symbol: str
    side: str
    quantity: int
    fill_price: float
    commission: float
    status: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class PaperTrader:
    """Paper trader that can use IBKR paper orders or local simulation."""

    def __init__(self, ibkr_client: object | None = None, commission_per_share: float = 0.005) -> None:
        self.ibkr_client = ibkr_client
        self.commission_per_share = commission_per_share
        self._next_order_id = 1
        self.fills: list[PaperFill] = []

    def place_market_order(
        self,
        symbol: str,
        asset_class: str,
        side: str,
        quantity: int,
        reference_price: float,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> PaperFill:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.ibkr_client is not None and getattr(self.ibkr_client, "is_connected", False):
            trade = self.ibkr_client.place_order(
                symbol=symbol,
                asset_class=asset_class,
                exchange=exchange,
                currency=currency,
                order_request=OrderRequest(side=side, quantity=quantity, order_type="MKT"),
            )
            order_id = str(trade.order.orderId)
            status = trade.orderStatus.status
            fill_price = float(trade.orderStatus.avgFillPrice or reference_price)
        else:
            order_id = f"PAPER-{self._next_order_id}"
            self._next_order_id += 1
            status = "Filled"
            fill_price = reference_price
        fill = PaperFill(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            fill_price=fill_price,
            commission=quantity * self.commission_per_share,
            status=status,
        )
        self.fills.append(fill)
        return fill

    def open_trades(self) -> list[dict[str, Any]]:
        return [fill.__dict__ for fill in self.fills if fill.status.lower() in {"filled", "submitted"}]
