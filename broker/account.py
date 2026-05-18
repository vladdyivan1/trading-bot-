"""Account summary helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AccountSnapshot:
    net_liquidation: float
    available_funds: float
    buying_power: float
    currency: str = "USD"


def parse_account_summary(rows: list[object]) -> dict[str, str]:
    """Convert ib_insync account summary rows into a tag/value dictionary."""

    summary: dict[str, str] = {}
    for row in rows:
        tag = getattr(row, "tag", None)
        value = getattr(row, "value", None)
        currency = getattr(row, "currency", "")
        if tag is not None and value is not None:
            summary[tag] = f"{value} {currency}".strip()
    return summary
