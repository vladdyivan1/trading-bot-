"""Tradier adapter stub for future live options execution."""

from __future__ import annotations

from backend.schemas.decision import ExecutionResult
from execution.broker_base import BrokerAdapter, OrderRequest


class TradierAdapter(BrokerAdapter):
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        raise NotImplementedError(
            "Tradier live execution is intentionally disabled. Enable broker execution "
            "and implement authenticated order routing before using this adapter."
        )
