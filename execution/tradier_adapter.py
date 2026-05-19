"""Tradier broker adapter stub — enable with LIVE mode + credentials."""

import logging
from typing import Any, Optional

from execution.broker_base import BrokerAdapter, OrderRequest, OrderResult

logger = logging.getLogger(__name__)


class TradierAdapter(BrokerAdapter):
    def __init__(self, api_key: str, account_id: str, sandbox: bool = True):
        self.api_key = api_key
        self.account_id = account_id
        self.sandbox = sandbox
        self._connected = False

    def connect(self) -> bool:
        logger.info("Tradier adapter stub — implement with Tradier REST API")
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def place_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError("Tradier live execution not enabled in MVP")

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> list[dict]:
        return []
