"""Alpaca adapter stub for future equity/options routing."""

import logging
from typing import Any, Optional

from execution.broker_base import BrokerAdapter, OrderRequest, OrderResult

logger = logging.getLogger(__name__)


class AlpacaAdapter(BrokerAdapter):
    def connect(self) -> bool:
        logger.info("Alpaca adapter stub")
        return False

    def disconnect(self) -> None:
        pass

    def place_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError("Alpaca options support varies — implement per account tier")

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> list[dict]:
        return []
