"""Base strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from schemas import Direction, TradeSignal


class BaseStrategy(ABC):
    """Abstract trading strategy with indicator and signal hooks."""

    name: str = "base"

    def __init__(self, params: dict | None = None) -> None:
        self.params = params or {}

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to OHLCV dataframe."""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> TradeSignal | None:
        """Return a trade signal for the latest bar, or None."""

    def get_entry(self, df: pd.DataFrame) -> float | None:
        if df.empty:
            return None
        col = "close" if "close" in df.columns else "Close"
        return float(df[col].iloc[-1])

    def get_exit(self, df: pd.DataFrame, direction: Direction) -> float | None:
        return self.get_entry(df)

    def get_stop_loss(
        self, entry: float, df: pd.DataFrame, direction: Direction, atr_mult: float = 1.5
    ) -> float:
        atr = self._atr(df)
        if direction == Direction.LONG:
            return entry - atr * atr_mult
        return entry + atr * atr_mult

    def get_take_profit(
        self, entry: float, df: pd.DataFrame, direction: Direction, atr_mult: float = 2.0
    ) -> float:
        atr = self._atr(df)
        if direction == Direction.LONG:
            return entry + atr * atr_mult
        return entry - atr * atr_mult

    def _atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df["high"] if "high" in df.columns else df["High"]
        low = df["low"] if "low" in df.columns else df["Low"]
        close = df["close"] if "close" in df.columns else df["Close"]
        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr) if pd.notna(atr) and atr > 0 else float(close.iloc[-1] * 0.01)
