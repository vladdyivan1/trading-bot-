"""Abstract execution adapter interface."""
from abc import ABC, abstractmethod

from backend.config import Settings, get_settings
from backend.schemas.execution import ExecutionResult, OptionContract


class BrokerAdapter(ABC):
    @abstractmethod
    async def open_position(
        self, contract: OptionContract, quantity: int, size_modifier: float = 1.0
    ) -> ExecutionResult:
        pass

    @abstractmethod
    async def close_position(self, order_id: str, reason: str = "signal") -> ExecutionResult:
        pass

    @abstractmethod
    async def get_open_positions(self) -> list[ExecutionResult]:
        pass


def get_executor(settings: Settings | None = None) -> BrokerAdapter:
    settings = settings or get_settings()
    if settings.execution_mode == "live" and settings.enable_broker_execution:
        # Future: route by configured broker
        from execution.tradier_adapter import TradierAdapter

        return TradierAdapter(settings)
    from execution.paper_executor import PaperExecutor

    return PaperExecutor(settings)
