"""Price breakout strategy with optional volume filter."""

from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy, StrategySignal


class BreakoutStrategy(BaseStrategy):
    name = "breakout"

    def __init__(self, lookback: int = 20, rr_ratio: float = 2.0, volume_multiplier: float = 1.2) -> None:
        self.lookback = lookback
        self.rr_ratio = rr_ratio
        self.volume_multiplier = volume_multiplier

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["rolling_high"] = df["high"].rolling(self.lookback).max()
        df["rolling_low"] = df["low"].rolling(self.lookback).min()
        if "volume" in df.columns:
            df["avg_volume"] = df["volume"].rolling(self.lookback).mean()
        else:
            df["volume"] = 0.0
            df["avg_volume"] = 0.0
        df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
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
        if len(df) < self.lookback + 2:
            return None

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        breakout_up = float(latest["close"]) > float(previous["rolling_high"])
        breakout_down = float(latest["close"]) < float(previous["rolling_low"])
        volume_ok = float(latest["volume"]) >= float(latest["avg_volume"]) * self.volume_multiplier if float(latest["avg_volume"]) > 0 else True

        direction = None
        if breakout_up and volume_ok:
            direction = "long"
        elif breakout_down and volume_ok:
            direction = "short"

        if direction is None:
            return None

        entry = self.get_entry(latest)
        stop = self.get_stop_loss(latest, direction)
        tp = self.get_take_profit(latest, direction)
        confidence = 0.7 if volume_ok else 0.55

        return StrategySignal(
            symbol=symbol,
            asset_class=asset_class,
            timeframe=timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=max(0.0001, stop),
            take_profit=max(0.0001, tp),
            confidence_score=confidence,
            reason="Breakout with volume confirmation",
            strategy_name=self.name,
            timestamp=df.index[-1].to_pydatetime() if isinstance(df.index[-1], pd.Timestamp) else None,
        )
