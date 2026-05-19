"""Live trading — disabled by default."""

from __future__ import annotations

from loguru import logger

from execution.paper_trader import PaperTrader
from schemas import TradeSignal


class LiveTrader(PaperTrader):
    """Live execution — requires explicit config and human approval."""

    def execute(self, signal: TradeSignal, quantity: int, human_approved: bool = False) -> dict:
        if not self.client.settings.live_trading_enabled:
            raise PermissionError(
                "Live trading is disabled. Set LIVE_TRADING_ENABLED=true in .env"
            )
        if not human_approved:
            raise PermissionError("Live trades require human_approved=True")
        if self.client.settings.paper_trading:
            logger.warning("Executing on paper account despite LiveTrader class")
        return super().execute(signal, quantity)
