"""Moving average crossover strategy."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from schemas import AssetClass, Direction, Timeframe, TradeSignal
from strategies.base_strategy import BaseStrategy


class MovingAverageCrossoverStrategy(BaseStrategy):
    name = "ma_crossover"

    def __init__(
        self,
        symbol: str,
        fast_period: int = 10,
        slow_period: int = 30,
        atr_multiplier: float = 1.5,
        **kwargs,
    ):
        super().__init__(symbol, **kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_multiplier = atr_multiplier

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df["sma_fast"] = df["close"].rolling(self.fast_period).mean()
        df["sma_slow"] = df["close"].rolling(self.slow_period).mean()
        df["atr"] = (
            pd.concat(
                [
                    df["high"] - df["low"],
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs(),
                ],
                axis=1,
            )
            .max(axis=1)
            .rolling(14)
            .mean()
        )
        df["cross_up"] = (df["sma_fast"] > df["sma_slow"]) & (
            df["sma_fast"].shift(1) <= df["sma_slow"].shift(1)
        )
        df["cross_down"] = (df["sma_fast"] < df["sma_slow"]) & (
            df["sma_fast"].shift(1) >= df["sma_slow"].shift(1)
        )
        return df

    def generate_signal(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        row = df.iloc[-1]
        if pd.isna(row.get("sma_fast")) or pd.isna(row.get("atr")):
            return None

        entry = float(row["close"])
        atr = float(row["atr"]) if row["atr"] > 0 else entry * 0.01

        if row.get("cross_up", False):
            direction = Direction.LONG
            stop = self.get_stop_loss(df, direction, entry)
            target = self.get_take_profit(df, direction, entry)
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target,
                confidence_score=0.65,
                reason="Fast MA crossed above slow MA",
                strategy_name=self.name,
            )
        if row.get("cross_down", False):
            direction = Direction.SHORT
            stop = self.get_stop_loss(df, direction, entry)
            target = self.get_take_profit(df, direction, entry)
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target,
                confidence_score=0.65,
                reason="Fast MA crossed below slow MA",
                strategy_name=self.name,
            )
        return None

    def get_stop_loss(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier
        if direction == Direction.LONG:
            return entry - offset
        return entry + offset

    def get_take_profit(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier * 2
        if direction == Direction.LONG:
            return entry + offset
        return entry - offset
