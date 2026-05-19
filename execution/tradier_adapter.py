"""Tradier broker adapter stub — live execution disabled by default."""
import logging

from backend.config import Settings
from backend.schemas.execution import ExecutionResult, OptionContract
from execution.broker_base import BrokerAdapter

logger = logging.getLogger(__name__)


class TradierAdapter(BrokerAdapter):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.token = settings.tradier_access_token
        self.account_id = settings.tradier_account_id

    async def open_position(
        self, contract: OptionContract, quantity: int, size_modifier: float = 1.0
    ) -> ExecutionResult:
        if not self.token or not self.account_id:
            return ExecutionResult(
                success=False,
                order_id="",
                side="buy",
                quantity=quantity,
                entry_price=0.0,
                status="rejected",
                message="Tradier credentials not configured",
            )
        logger.info("Tradier stub: would place %s x%d", contract.symbol, quantity)
        return ExecutionResult(
            success=False,
            order_id="",
            side="buy",
            quantity=quantity,
            entry_price=0.0,
            status="rejected",
            message="Tradier adapter is a stub — implement order placement before live use",
        )

    async def close_position(self, order_id: str, reason: str = "signal") -> ExecutionResult:
        return ExecutionResult(
            success=False,
            order_id=order_id,
            side="sell",
            quantity=0,
            entry_price=0.0,
            status="rejected",
            message="Tradier stub",
        )

    async def get_open_positions(self) -> list[ExecutionResult]:
        return []
