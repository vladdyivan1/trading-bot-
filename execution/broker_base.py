"""Execution adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.schemas.decision import ExecutionResult
from backend.services.options_selector import OptionContract


@dataclass(frozen=True)
class OrderRequest:
    contract: OptionContract
    side: str
    quantity: int
    max_price: float
    metadata: dict


class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order(self, request: OrderRequest) -> ExecutionResult:
        """Submit an options order and return a normalized result."""
