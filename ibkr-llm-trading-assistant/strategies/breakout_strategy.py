"""Price breakout strategy with volume confirmation."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from schemas import Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    name = "breakout"

    def __init__(
        self,
        symbol: str,
        lookback: int = 20,
        volume_multiplier: float = 1.5,
        atr_multiplier: float = 1.5,
        **kwargs,
    ):
        super().__init__(symbol, **kwargs)
        self.lookback = lookback
        self.volume_multiplier = volume_multiplier
        self.atr_multiplier = atr_multiplier

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df["high_n"] = df["high"].rolling(self.lookback).max()
        df["low_n"] = df["low"].rolling(self.lookback).min()
        df["avg_volume"] = df["volume"].rolling(self.lookback).mean()
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
        return df

    def generate_signal(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        if len(df) < self.lookback + 1:
            return None
        row = df.iloc[-1]
        prev = df.iloc[-2]
        if pd.isna(row.get("high_n")):
            return None

        entry = float(row["close"])
        vol_confirm = row["volume"] > row["avg_volume"] * self.volume_multiplier

        if row["close"] > prev["high_n"] and vol_confirm:
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=Direction.LONG,
                entry_price=entry,
                stop_loss=self.get_stop_loss(df, Direction.LONG, entry),
                take_profit=self.get_take_profit(df, Direction.LONG, entry),
                confidence_score=0.72,
                reason="Trend breakout with volume confirmation",
                strategy_name=self.name,
            )
        if row["close"] < prev["low_n"] and vol_confirm:
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=Direction.SHORT,
                entry_price=entry,
                stop_loss=self.get_stop_loss(df, Direction.SHORT, entry),
                take_profit=self.get_take_profit(df, Direction.SHORT, entry),
                confidence_score=0.72,
                reason="Downside breakout with volume confirmation",
                strategy_name=self.name,
            )
        return None

    def get_stop_loss(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier
        return entry - offset if direction == Direction.LONG else entry + offset

    def get_take_profit(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier * 2.0
        return entry + offset if direction == Direction.LONG else entry - offset
