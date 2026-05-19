"""Order construction and validation."""

from __future__ import annotations

from ib_insync import LimitOrder, MarketOrder, Order, StopOrder

from schemas import Direction


def build_market_order(
    action: str,
    quantity: float,
    tif: str = "DAY",
) -> MarketOrder:
    """Create a market order."""
    order = MarketOrder(action.upper(), quantity)
    order.tif = tif
    return order


def build_limit_order(
    action: str,
    quantity: float,
    limit_price: float,
    tif: str = "DAY",
) -> LimitOrder:
    """Create a limit order."""
    order = LimitOrder(action.upper(), quantity, limit_price)
    order.tif = tif
    return order


def build_bracket_orders(
    direction: Direction,
    quantity: float,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    use_market_entry: bool = True,
) -> list[Order]:
    """Build entry + stop + target bracket orders."""
    action = "BUY" if direction == Direction.LONG else "SELL"
    exit_action = "SELL" if direction == Direction.LONG else "BUY"

    if use_market_entry:
        parent = MarketOrder(action, quantity)
    else:
        parent = LimitOrder(action, quantity, entry_price)

    parent.transmit = False
    parent.orderId = 1

    stop = StopOrder(exit_action, quantity, stop_loss)
    stop.parentId = parent.orderId
    stop.transmit = False

    take = LimitOrder(exit_action, quantity, take_profit)
    take.parentId = parent.orderId
    take.transmit = True

    return [parent, stop, take]


def direction_to_action(direction: Direction, is_entry: bool = True) -> str:
    """Map signal direction to IBKR action."""
    if direction == Direction.LONG:
        return "BUY" if is_entry else "SELL"
    if direction == Direction.SHORT:
        return "SELL" if is_entry else "BUY"
    raise ValueError("Cannot place order for flat direction")
