"""Base strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from schemas import AssetClass, Direction, Timeframe, TradeSignal


class BaseStrategy(ABC):
    """Abstract trading strategy."""

    name: str = "base"

    def __init__(
        self,
        symbol: str,
        asset_class: AssetClass = AssetClass.STK,
        timeframe: Timeframe = Timeframe.M5,
    ):
        self.symbol = symbol
        self.asset_class = asset_class
        self.timeframe = timeframe

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to OHLCV dataframe."""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        """Generate trade signal from latest bar data."""

    def get_entry(self, df: pd.DataFrame) -> Optional[float]:
        if df.empty:
            return None
        return float(df.iloc[-1]["close"])

    def get_exit(self, df: pd.DataFrame, direction: Direction) -> Optional[float]:
        return self.get_entry(df)

    @abstractmethod
    def get_stop_loss(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        pass

    @abstractmethod
    def get_take_profit(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        pass

    def run(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        """Full pipeline: indicators -> signal."""
        if len(df) < 20:
            return None
        enriched = self.calculate_indicators(df.copy())
        return self.generate_signal(enriched)
