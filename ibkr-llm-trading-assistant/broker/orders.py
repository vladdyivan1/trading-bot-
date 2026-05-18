"""Order construction and validation."""

from __future__ import annotations

from ib_insync import LimitOrder, MarketOrder, Order, StopOrder

from schemas import Direction, OrderSide, TradeSignal


def signal_to_order_side(direction: Direction, is_entry: bool = True) -> str:
    """Map signal direction to IB order action."""
    if direction == Direction.LONG:
        return "BUY" if is_entry else "SELL"
    if direction == Direction.SHORT:
        return "SELL" if is_entry else "BUY"
    raise ValueError(f"Cannot create order for direction: {direction}")


def create_market_order(action: str, quantity: float) -> MarketOrder:
    return MarketOrder(action, quantity)


def create_limit_order(action: str, quantity: float, limit_price: float) -> LimitOrder:
    return LimitOrder(action, quantity, limit_price)


def create_stop_order(action: str, quantity: float, stop_price: float) -> StopOrder:
    return StopOrder(action, quantity, stop_price)


def create_bracket_orders(
    signal: TradeSignal,
    quantity: float,
) -> tuple[Order, Order, Order]:
    """Create entry + stop loss + take profit bracket."""
    entry_action = signal_to_order_side(signal.direction, is_entry=True)
    exit_action = signal_to_order_side(signal.direction, is_entry=False)

    parent = LimitOrder(entry_action, quantity, signal.entry_price)
    parent.transmit = False

    stop = StopOrder(exit_action, quantity, signal.stop_loss)
    stop.parentId = parent.orderId
    stop.transmit = False

    take_profit = LimitOrder(exit_action, quantity, signal.take_profit)
    take_profit.parentId = parent.orderId
    take_profit.transmit = True

    return parent, stop, take_profit


def validate_order_quantity(quantity: float, max_contracts: int) -> bool:
    return 0 < quantity <= max_contracts
