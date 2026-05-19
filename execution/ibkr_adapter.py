"""Interactive Brokers adapter stub for future live options execution."""

from __future__ import annotations

from backend.schemas.decision import ExecutionResult
from execution.broker_base import BrokerAdapter, OrderRequest


class IbkrAdapter(BrokerAdapter):
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        raise NotImplementedError(
            "IBKR live execution is intentionally disabled. Wire this adapter to an "
            "audited options order service before enabling live mode."
        )
