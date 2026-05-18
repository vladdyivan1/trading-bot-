"""RSI mean reversion strategy."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from schemas import Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


class RSIMeanReversionStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def __init__(
        self,
        symbol: str,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        atr_multiplier: float = 1.5,
        **kwargs,
    ):
        super().__init__(symbol, **kwargs)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.atr_multiplier = atr_multiplier

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))
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
        row = df.iloc[-1]
        prev = df.iloc[-2]
        if pd.isna(row.get("rsi")):
            return None

        entry = float(row["close"])
        rsi = float(row["rsi"])

        if prev["rsi"] < self.oversold <= rsi or rsi < self.oversold:
            direction = Direction.LONG
            confidence = min(0.85, 0.5 + (self.oversold - rsi) / 100)
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=self.get_stop_loss(df, direction, entry),
                take_profit=self.get_take_profit(df, direction, entry),
                confidence_score=max(0.55, confidence),
                reason=f"RSI oversold at {rsi:.1f}",
                strategy_name=self.name,
            )
        if prev["rsi"] > self.overbought >= rsi or rsi > self.overbought:
            direction = Direction.SHORT
            confidence = min(0.85, 0.5 + (rsi - self.overbought) / 100)
            return TradeSignal(
                symbol=self.symbol,
                asset_class=self.asset_class,
                timeframe=self.timeframe,
                direction=direction,
                entry_price=entry,
                stop_loss=self.get_stop_loss(df, direction, entry),
                take_profit=self.get_take_profit(df, direction, entry),
                confidence_score=max(0.55, confidence),
                reason=f"RSI overbought at {rsi:.1f}",
                strategy_name=self.name,
            )
        return None

    def get_stop_loss(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier
        return entry - offset if direction == Direction.LONG else entry + offset

    def get_take_profit(self, df: pd.DataFrame, direction: Direction, entry: float) -> float:
        atr = float(df.iloc[-1].get("atr", entry * 0.01))
        offset = atr * self.atr_multiplier * 2.5
        return entry + offset if direction == Direction.LONG else entry - offset
