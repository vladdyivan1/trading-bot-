from __future__ import annotations

from execution.broker_base import ExecutionAdapter, ExecutionRequest, ExecutionResult


class TradierExecutionAdapter(ExecutionAdapter):
    """Stub for future Tradier options routing."""

    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            status="NOT_IMPLEMENTED",
            reason="Tradier adapter stub. Enable when broker wiring is complete.",
        )

    def open_positions(self) -> list[dict]:
        return []
