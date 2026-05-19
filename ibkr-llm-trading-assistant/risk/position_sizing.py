"""Position sizing based on account risk."""

from __future__ import annotations

import math

from schemas import TradeSignal


def size_by_risk(
    account_value: float,
    signal: TradeSignal,
    risk_pct: float = 0.5,
    max_contracts: int = 1000,
) -> int:
    """
    Calculate position size so risk per trade equals risk_pct of account.

    Returns integer share/contract count (minimum 1 if approved).
    """
    risk_per_share = abs(signal.entry_price - signal.stop_loss)
    if risk_per_share <= 0 or account_value <= 0:
        return 0
    risk_amount = account_value * (risk_pct / 100.0)
    shares = risk_amount / risk_per_share
    shares = min(shares, max_contracts)
    return max(0, int(math.floor(shares)))
