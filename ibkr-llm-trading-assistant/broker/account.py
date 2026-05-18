"""Account summary and position helpers."""

from __future__ import annotations

from typing import Any

from ib_insync import IB


def get_account_summary(ib: IB) -> dict[str, Any]:
    """Fetch account summary as a dict."""
    ib.reqAccountSummary()
    ib.sleep(1)
    summary: dict[str, Any] = {}
    for item in ib.accountSummary():
        summary[item.tag] = item.value
    return summary


def get_net_liquidation(ib: IB) -> float:
    summary = get_account_summary(ib)
    for key in ("NetLiquidation", "TotalCashValue"):
        if key in summary:
            try:
                return float(summary[key])
            except (TypeError, ValueError):
                continue
    return 0.0


def get_positions(ib: IB) -> list[dict[str, Any]]:
    """Return open positions as dicts."""
    positions = []
    for pos in ib.positions():
        positions.append(
            {
                "symbol": pos.contract.symbol,
                "sec_type": pos.contract.secType,
                "position": pos.position,
                "avg_cost": pos.avgCost,
                "account": pos.account,
            }
        )
    return positions


def count_open_positions(ib: IB) -> int:
    return len([p for p in ib.positions() if p.position != 0])
