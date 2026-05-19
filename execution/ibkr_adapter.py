from __future__ import annotations

from execution.broker_base import ExecutionAdapter, ExecutionRequest, ExecutionResult


class IBKRExecutionAdapter(ExecutionAdapter):
    """Stub for Interactive Brokers options routing."""

    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            status="NOT_IMPLEMENTED",
            reason="IBKR adapter stub. Keep paper mode enabled until implemented.",
        )

    def open_positions(self) -> list[dict]:
        return []
