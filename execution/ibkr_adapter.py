"""Interactive Brokers adapter stub."""

import logging
from typing import Any, Optional

from execution.broker_base import BrokerAdapter, OrderRequest, OrderResult

logger = logging.getLogger(__name__)


class IBKRAdapter(BrokerAdapter):
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id

    def connect(self) -> bool:
        logger.info("IBKR adapter stub — wire to ib_insync or TWS API")
        return False

    def disconnect(self) -> None:
        pass

    def place_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError("IBKR live execution not enabled in MVP")

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> list[dict]:
        return []
