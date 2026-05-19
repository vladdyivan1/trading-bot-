from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.schemas.decision import OptionDirection


@dataclass(slots=True)
class OptionContractCandidate:
    symbol: str
    expiration: date
    strike: float
    delta: float
    bid: float
    ask: float
    open_interest: int
    volume: int

    @property
    def spread_pct(self) -> float:
        mid = (self.bid + self.ask) / 2
        if mid <= 0:
            return 1.0
        return max(self.ask - self.bid, 0) / mid

    @property
    def mid_price(self) -> float:
        return max((self.bid + self.ask) / 2, 0.01)


@dataclass(slots=True)
class ExecutionRequest:
    underlying_symbol: str
    direction: OptionDirection
    underlying_price: float
    quantity: int
    max_spread_pct: float
    delta_min: float
    delta_max: float
    dte_preference: int
    dte_fallback: int
    min_open_interest: int
    min_volume: int
    max_hold_minutes: int
    metadata: dict[str, Any]


@dataclass(slots=True)
class ExecutionResult:
    accepted: bool
    status: str
    reason: str
    contract_symbol: str | None = None
    expiration: str | None = None
    strike: float | None = None
    delta: float | None = None
    quantity: int = 0
    fill_price: float = 0.0
    spread_pct: float = 0.0
    metadata: dict[str, Any] | None = None


class ExecutionAdapter(ABC):
    @abstractmethod
    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def open_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError
