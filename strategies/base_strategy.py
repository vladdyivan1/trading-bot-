"""Base strategy contracts and signal models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field


class StrategySignal(BaseModel):
    """Structured signal consumed by risk and execution layers."""

    symbol: str
    asset_class: str = "STK"
    timeframe: str
    direction: Literal["long", "short"]
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    confidence_score: float = Field(ge=0, le=1)
    reason: str
    strategy_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def reward_risk(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        if risk == 0:
            return 0.0
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk


class BaseStrategy(ABC):
    """Deterministic base class for all strategies."""

    name: str = "base"

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def generate_signal(
        self,
        data: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
    ) -> StrategySignal | None:
        raise NotImplementedError

    @abstractmethod
    def get_entry(self, row: pd.Series) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_exit(self, row: pd.Series) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_stop_loss(self, row: pd.Series, direction: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_take_profit(self, row: pd.Series, direction: str) -> float:
        raise NotImplementedError
