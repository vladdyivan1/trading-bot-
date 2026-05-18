"""Order construction and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

try:
    from ib_insync import LimitOrder, MarketOrder, Order, StopOrder
except ImportError:  # pragma: no cover
    LimitOrder = MarketOrder = StopOrder = None  # type: ignore[assignment]
    Order = object  # type: ignore[assignment]

OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MKT", "LMT", "STP"]


@dataclass(frozen=True)
class OrderRequest:
    side: OrderSide
    quantity: float
    order_type: OrderType = "MKT"
    limit_price: float | None = None
    stop_price: float | None = None
    transmit: bool = True


def build_order(request: OrderRequest) -> Order:
    """Build an ib_insync order from a validated request."""

    if MarketOrder is None:
        raise RuntimeError("ib_insync is required for order creation")
    if request.quantity <= 0:
        raise ValueError("Order quantity must be positive")
    if request.order_type == "MKT":
        return MarketOrder(request.side, request.quantity, transmit=request.transmit)
    if request.order_type == "LMT":
        if request.limit_price is None or request.limit_price <= 0:
            raise ValueError("Limit orders require a positive limit_price")
        return LimitOrder(request.side, request.quantity, request.limit_price, transmit=request.transmit)
    if request.order_type == "STP":
        if request.stop_price is None or request.stop_price <= 0:
            raise ValueError("Stop orders require a positive stop_price")
        return StopOrder(request.side, request.quantity, request.stop_price, transmit=request.transmit)
    raise ValueError(f"Unsupported order type: {request.order_type}")
