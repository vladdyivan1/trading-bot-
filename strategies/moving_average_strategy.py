"""Moving-average crossover strategy."""

from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy, TradeSignal, average_true_range


class MovingAverageCrossoverStrategy(BaseStrategy):
    """Generate long/short signals when fast and slow averages cross."""

    name = "moving_average_crossover"

    def __init__(
        self,
        symbol: str,
        asset_class: str = "STK",
        timeframe: str = "1 day",
        fast_window: int = 20,
        slow_window: int = 50,
    ) -> None:
        super().__init__(symbol, asset_class, timeframe)  # type: ignore[arg-type]
        if fast_window >= slow_window:
            raise ValueError("fast_window must be less than slow_window")
        self.fast_window = fast_window
        self.slow_window = slow_window

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["fast_ma"] = df["close"].rolling(self.fast_window, min_periods=self.fast_window).mean()
        df["slow_ma"] = df["close"].rolling(self.slow_window, min_periods=self.slow_window).mean()
        df["atr"] = average_true_range(df)
        df["volume_ma"] = df["volume"].rolling(20, min_periods=1).mean() if "volume" in df else 0
        return df

    def generate_signal(self, data: pd.DataFrame) -> TradeSignal | None:
        df = self.calculate_indicators(data).dropna(subset=["fast_ma", "slow_ma"])
        if len(df) < 2:
            return None

        prev = df.iloc[-2]
        latest = df.iloc[-1]
        direction = None
        reason = ""
        if prev["fast_ma"] <= prev["slow_ma"] and latest["fast_ma"] > latest["slow_ma"]:
            direction = "long"
            reason = "Fast moving average crossed above slow moving average."
        elif prev["fast_ma"] >= prev["slow_ma"] and latest["fast_ma"] < latest["slow_ma"]:
            direction = "short"
            reason = "Fast moving average crossed below slow moving average."

        if direction is None:
            return None

        entry = self.get_entry(latest)
        stop = self.get_stop_loss(latest, direction)
        target = self.get_take_profit(latest, direction)
        ma_distance = abs(float(latest["fast_ma"] - latest["slow_ma"])) / max(entry, 1e-9)
        confidence = min(0.95, 0.55 + ma_distance * 10)
        return TradeSignal(
            symbol=self.symbol,
            asset_class=self.asset_class,
            timeframe=self.timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
            confidence_score=confidence,
            reason=reason,
            metadata={"fast_window": self.fast_window, "slow_window": self.slow_window},
        )
