"""RSI mean-reversion strategy."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base_strategy import BaseStrategy, StrategySignal


class RSIStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def __init__(self, rsi_window: int = 14, oversold: float = 30, overbought: float = 70, rr_ratio: float = 1.8) -> None:
        self.rsi_window = rsi_window
        self.oversold = oversold
        self.overbought = overbought
        self.rr_ratio = rr_ratio

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        avg_gain = up.rolling(self.rsi_window).mean()
        avg_loss = down.rolling(self.rsi_window).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        tr = np.maximum(df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1))))
        df["atr"] = tr.rolling(self.rsi_window).mean()
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
        if len(df) < self.rsi_window + 2:
            return None

        latest = df.iloc[-1]
        rsi = float(latest.get("rsi", np.nan))
        if np.isnan(rsi):
            return None

        direction = None
        if rsi <= self.oversold:
            direction = "long"
        elif rsi >= self.overbought:
            direction = "short"

        if direction is None:
            return None

        entry = self.get_entry(latest)
        stop = self.get_stop_loss(latest, direction)
        tp = self.get_take_profit(latest, direction)
        distance = abs(rsi - 50) / 50
        confidence = max(0.0, min(1.0, distance))

        return StrategySignal(
            symbol=symbol,
            asset_class=asset_class,
            timeframe=timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=max(0.0001, stop),
            take_profit=max(0.0001, tp),
            confidence_score=confidence,
            reason=f"RSI mean reversion trigger at RSI={rsi:.2f}",
            strategy_name=self.name,
            timestamp=df.index[-1].to_pydatetime() if isinstance(df.index[-1], pd.Timestamp) else None,
        )
