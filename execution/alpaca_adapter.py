"""Alpaca broker adapter stub for future live options/stock routing."""
import logging

from backend.config import Settings
from backend.schemas.execution import ExecutionResult, OptionContract
from execution.broker_base import BrokerAdapter

logger = logging.getLogger(__name__)


class AlpacaAdapter(BrokerAdapter):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def open_position(
        self, contract: OptionContract, quantity: int, size_modifier: float = 1.0
    ) -> ExecutionResult:
        logger.info("Alpaca stub: %s qty=%d", contract.symbol, quantity)
        return ExecutionResult(
            success=False,
            order_id="",
            side="buy",
            quantity=quantity,
            entry_price=0.0,
            status="rejected",
            message="Alpaca adapter is a stub — configure Alpaca options API before live use",
        )

    async def close_position(self, order_id: str, reason: str = "signal") -> ExecutionResult:
        return ExecutionResult(
            success=False,
            order_id=order_id,
            side="sell",
            quantity=0,
            entry_price=0.0,
            status="rejected",
            message="Alpaca stub",
        )

    async def get_open_positions(self) -> list[ExecutionResult]:
        return []
