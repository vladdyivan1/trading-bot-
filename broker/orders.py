"""Order builders for deterministic execution paths."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    side: Literal["BUY", "SELL"]
    quantity: int = Field(gt=0)
    order_type: Literal["MKT", "LMT"] = "MKT"
    limit_price: float | None = None
    tif: str = "DAY"


def build_order(order_request: OrderRequest):
    """Translate generic order request into ib_insync order."""

    try:
        from ib_insync import LimitOrder, MarketOrder
    except ImportError as exc:  # pragma: no cover - integration-only path
        raise RuntimeError("ib_insync is required to build broker orders") from exc

    if order_request.order_type == "MKT":
        return MarketOrder(order_request.side, order_request.quantity, tif=order_request.tif)

    if order_request.limit_price is None:
        raise ValueError("limit_price is required for LMT orders")

    return LimitOrder(
        order_request.side,
        order_request.quantity,
        order_request.limit_price,
        tif=order_request.tif,
    )
