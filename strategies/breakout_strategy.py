"""Price breakout strategy with volume confirmation."""

from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy, TradeSignal, average_true_range


class BreakoutStrategy(BaseStrategy):
    """Trade breakouts beyond recent highs/lows."""

    name = "breakout"

    def __init__(
        self,
        symbol: str,
        asset_class: str = "STK",
        timeframe: str = "1 day",
        lookback: int = 20,
        volume_multiplier: float = 1.2,
    ) -> None:
        super().__init__(symbol, asset_class, timeframe)  # type: ignore[arg-type]
        self.lookback = lookback
        self.volume_multiplier = volume_multiplier

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["prior_high"] = df["high"].shift(1).rolling(self.lookback, min_periods=self.lookback).max()
        df["prior_low"] = df["low"].shift(1).rolling(self.lookback, min_periods=self.lookback).min()
        df["atr"] = average_true_range(df)
        if "volume" in df:
            df["volume_ma"] = df["volume"].rolling(self.lookback, min_periods=1).mean()
        else:
            df["volume"] = 0
            df["volume_ma"] = 0
        return df

    def generate_signal(self, data: pd.DataFrame) -> TradeSignal | None:
        df = self.calculate_indicators(data).dropna(subset=["prior_high", "prior_low"])
        if df.empty:
            return None

        latest = df.iloc[-1]
        volume_ok = latest["volume_ma"] == 0 or latest["volume"] >= latest["volume_ma"] * self.volume_multiplier
        direction = None
        if latest["close"] > latest["prior_high"] and volume_ok:
            direction = "long"
            reason = "Trend breakout above prior range with volume confirmation."
        elif latest["close"] < latest["prior_low"] and volume_ok:
            direction = "short"
            reason = "Breakdown below prior range with volume confirmation."
        else:
            return None

        entry = self.get_entry(latest)
        range_width = max(float(latest["prior_high"] - latest["prior_low"]), 1e-9)
        breakout_strength = min(0.3, abs(float(latest["close"] - latest["prior_high"])) / range_width)
        return TradeSignal(
            symbol=self.symbol,
            asset_class=self.asset_class,
            timeframe=self.timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=self.get_stop_loss(latest, direction),
            take_profit=self.get_take_profit(latest, direction),
            confidence_score=min(0.95, 0.6 + breakout_strength),
            reason=reason,
            metadata={"lookback": self.lookback, "volume_multiplier": self.volume_multiplier},
        )
