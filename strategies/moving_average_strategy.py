"""Moving average crossover strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, StrategySignal


class MovingAverageStrategy(BaseStrategy):
    name = "moving_average_crossover"

    def __init__(self, fast_window: int = 20, slow_window: int = 50, atr_window: int = 14, rr_ratio: float = 2.0) -> None:
        self.fast_window = fast_window
        self.slow_window = slow_window
        self.atr_window = atr_window
        self.rr_ratio = rr_ratio

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["fast_ma"] = df["close"].rolling(self.fast_window).mean()
        df["slow_ma"] = df["close"].rolling(self.slow_window).mean()
        tr = np.maximum(df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1))))
        df["atr"] = tr.rolling(self.atr_window).mean()
        return df

    def get_entry(self, row: pd.Series) -> float:
        return float(row["close"])

    def get_exit(self, row: pd.Series) -> float:
        return float(row["close"])

    def get_stop_loss(self, row: pd.Series, direction: str) -> float:
        atr = float(row.get("atr", 0.0) or 0.0)
        if direction == "long":
            return float(row["close"] - atr)
        return float(row["close"] + atr)

    def get_take_profit(self, row: pd.Series, direction: str) -> float:
        entry = self.get_entry(row)
        stop = self.get_stop_loss(row, direction)
        if direction == "long":
            return float(entry + self.rr_ratio * (entry - stop))
        return float(entry - self.rr_ratio * (stop - entry))

    def generate_signal(self, data: pd.DataFrame, symbol: str, asset_class: str, timeframe: str) -> StrategySignal | None:
        df = self.calculate_indicators(data)
        if len(df) < self.slow_window + 2:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        if pd.isna(latest["fast_ma"]) or pd.isna(latest["slow_ma"]):
            return None

        direction = None
        if prev["fast_ma"] <= prev["slow_ma"] and latest["fast_ma"] > latest["slow_ma"]:
            direction = "long"
        elif prev["fast_ma"] >= prev["slow_ma"] and latest["fast_ma"] < latest["slow_ma"]:
            direction = "short"

        if direction is None:
            return None

        entry = self.get_entry(latest)
        stop = self.get_stop_loss(latest, direction)
        tp = self.get_take_profit(latest, direction)
        confidence = min(1.0, max(0.0, abs(float(latest["fast_ma"] - latest["slow_ma"])) / max(entry, 1e-6) * 200))

        return StrategySignal(
            symbol=symbol,
            asset_class=asset_class,
            timeframe=timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=max(0.0001, stop),
            take_profit=max(0.0001, tp),
            confidence_score=confidence,
            reason="MA crossover with ATR-based stop",
            strategy_name=self.name,
            timestamp=df.index[-1].to_pydatetime() if isinstance(df.index[-1], pd.Timestamp) else None,
        )
