"""Position sizing helpers."""

from __future__ import annotations

import math


def fixed_fractional_size(
    account_equity: float,
    entry_price: float,
    stop_loss: float,
    risk_fraction: float = 0.005,
    max_quantity: int | None = None,
) -> int:
    """Size a position by account risk and distance to stop."""

    if account_equity <= 0:
        return 0
    if entry_price <= 0 or stop_loss <= 0:
        return 0
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        return 0
    quantity = math.floor((account_equity * risk_fraction) / risk_per_unit)
    if max_quantity is not None:
        quantity = min(quantity, max_quantity)
    return max(0, quantity)


def notional_value(quantity: float, price: float, multiplier: float = 1.0) -> float:
    return abs(quantity * price * multiplier)
