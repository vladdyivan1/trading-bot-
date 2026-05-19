"""Abstract broker execution adapter."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str  # BUY | SELL
    quantity: int
    order_type: str = "MARKET"
    limit_price: Optional[float] = None


@dataclass
class OrderResult:
    success: bool
    fill_price: float
    order_id: str
    message: str = ""


class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        pass

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def get_option_chain(self, symbol: str, expiration: Optional[str] = None) -> list[dict]:
        pass
