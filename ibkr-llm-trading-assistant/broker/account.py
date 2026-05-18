"""Account summary and position helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from ib_insync import IB


def get_account_summary(ib: IB, account: str | None = None) -> dict[str, str]:
    """Fetch account summary tags as a dict."""
    account = account or ""
    tags = ib.accountSummary(account)
    return {item.tag: item.value for item in tags}


def get_net_liquidation(ib: IB, account: str | None = None) -> float:
    """Return NetLiquidation value."""
    summary = get_account_summary(ib, account)
    for key in ("NetLiquidation", "TotalCashValue"):
        if key in summary:
            try:
                return float(summary[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def get_positions_df(ib: IB) -> pd.DataFrame:
    """Return open positions as a DataFrame."""
    positions = ib.positions()
    if not positions:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for pos in positions:
        c = pos.contract
        rows.append(
            {
                "symbol": c.symbol,
                "sec_type": c.secType,
                "position": pos.position,
                "avg_cost": pos.avgCost,
                "account": pos.account,
            }
        )
    return pd.DataFrame(rows)
