"""Account service layer around IBKR account endpoints."""

from __future__ import annotations

from broker.ibkr_client import IBKRClient


class AccountService:
    def __init__(self, ibkr_client: IBKRClient) -> None:
        self.ibkr_client = ibkr_client

    def account_summary(self) -> dict[str, str]:
        return self.ibkr_client.get_account_summary()

    def open_positions(self) -> list[dict]:
        return self.ibkr_client.get_open_positions()

    def net_liquidation(self) -> float:
        summary = self.account_summary()
        return float(summary.get("NetLiquidation", 0.0))

    def available_funds(self) -> float:
        summary = self.account_summary()
        return float(summary.get("AvailableFunds", 0.0))
