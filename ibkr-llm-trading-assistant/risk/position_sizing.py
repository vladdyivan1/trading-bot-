"""Position sizing based on account risk."""

from __future__ import annotations

from schemas import TradeSignal


def calculate_position_size(
    account_value: float,
    signal: TradeSignal,
    risk_per_trade_pct: float,
    max_contracts: int,
) -> float:
    """
    Size position so max loss at stop equals risk_per_trade_pct of account.
    """
    risk_amount = account_value * (risk_per_trade_pct / 100)
    risk_per_unit = abs(signal.entry_price - signal.stop_loss)
    if risk_per_unit <= 0:
        return 0.0
    quantity = risk_amount / risk_per_unit
    if signal.asset_class.value == "CASH":
        quantity = min(quantity, account_value * 20 / signal.entry_price)
    return min(max(1, int(quantity)), max_contracts)
