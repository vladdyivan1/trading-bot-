"""Interactive Brokers adapter stub."""
import logging

from backend.config import Settings
from backend.schemas.execution import ExecutionResult, OptionContract
from execution.broker_base import BrokerAdapter

logger = logging.getLogger(__name__)


class IBKRAdapter(BrokerAdapter):
    def __init__(self, settings: Settings):
        self.host = settings.ibkr_host
        self.port = settings.ibkr_port
        self.client_id = settings.ibkr_client_id

    async def open_position(
        self, contract: OptionContract, quantity: int, size_modifier: float = 1.0
    ) -> ExecutionResult:
        logger.info(
            "IBKR stub: connect %s:%s client_id=%s",
            self.host,
            self.port,
            self.client_id,
        )
        return ExecutionResult(
            success=False,
            order_id="",
            side="buy",
            quantity=quantity,
            entry_price=0.0,
            status="rejected",
            message="IBKR adapter is a stub — wire ib_insync or TWS API before live use",
        )

    async def close_position(self, order_id: str, reason: str = "signal") -> ExecutionResult:
        return ExecutionResult(
            success=False,
            order_id=order_id,
            side="sell",
            quantity=0,
            entry_price=0.0,
            status="rejected",
            message="IBKR stub",
        )

    async def get_open_positions(self) -> list[ExecutionResult]:
        return []
