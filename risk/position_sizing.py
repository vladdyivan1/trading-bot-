"""Position sizing helpers."""

from __future__ import annotations


def calculate_position_size(
    account_equity: float,
    entry_price: float,
    stop_loss: float,
    max_risk_pct: float,
    contract_multiplier: float = 1.0,
    max_units: int | None = None,
) -> int:
    if entry_price <= 0 or stop_loss <= 0:
        return 0
    risk_amount = account_equity * (max_risk_pct / 100)
    risk_per_unit = abs(entry_price - stop_loss) * contract_multiplier
    if risk_per_unit <= 0:
        return 0
    units = int(risk_amount // risk_per_unit)
    if max_units is not None:
        units = min(units, max_units)
    return max(0, units)


def reward_risk_ratio(entry_price: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry_price - stop_loss)
    if risk == 0:
        return 0.0
    reward = abs(take_profit - entry_price)
    return reward / risk
