"""RSI mean-reversion strategy."""

from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy, TradeSignal, average_true_range


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Wilder-style RSI."""

    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


class RSIMeanReversionStrategy(BaseStrategy):
    """Buy oversold and sell short overbought conditions."""

    name = "rsi_mean_reversion"

    def __init__(
        self,
        symbol: str,
        asset_class: str = "STK",
        timeframe: str = "1 day",
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
    ) -> None:
        super().__init__(symbol, asset_class, timeframe)  # type: ignore[arg-type]
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df["rsi"] = rsi(df["close"], self.period)
        df["atr"] = average_true_range(df)
        df["sma_200"] = df["close"].rolling(200, min_periods=50).mean()
        return df

    def generate_signal(self, data: pd.DataFrame) -> TradeSignal | None:
        df = self.calculate_indicators(data).dropna(subset=["rsi"])
        if len(df) < 2:
            return None

        prev = df.iloc[-2]
        latest = df.iloc[-1]
        direction = None
        if prev["rsi"] < self.oversold and latest["rsi"] >= self.oversold:
            direction = "long"
            reason = "RSI recovered from oversold territory."
        elif prev["rsi"] > self.overbought and latest["rsi"] <= self.overbought:
            direction = "short"
            reason = "RSI retreated from overbought territory."
        else:
            return None

        entry = self.get_entry(latest)
        distance_from_threshold = (
            abs(float(latest["rsi"] - self.oversold))
            if direction == "long"
            else abs(float(self.overbought - latest["rsi"]))
        )
        confidence = min(0.9, 0.55 + distance_from_threshold / 100)
        return TradeSignal(
            symbol=self.symbol,
            asset_class=self.asset_class,
            timeframe=self.timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=self.get_stop_loss(latest, direction),
            take_profit=self.get_take_profit(latest, direction),
            confidence_score=confidence,
            reason=reason,
            metadata={"period": self.period, "oversold": self.oversold, "overbought": self.overbought},
        )
