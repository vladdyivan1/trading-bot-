"""RSI mean reversion strategy."""

from __future__ import annotations

import pandas as pd

from schemas import Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


class RSIStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params)
        self.period = int(self.params.get("rsi_period", 14))
        self.oversold = float(self.params.get("oversold", 30))
        self.overbought = float(self.params.get("overbought", 70))

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = out["close"] if "close" in out.columns else out["Close"]
        out["rsi"] = _rsi(close, self.period)
        return out

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal | None:
        if len(df) < self.period + 5:
            return None
        data = self.calculate_indicators(df)
        symbol = str(data["symbol"].iloc[-1]) if "symbol" in data.columns else self.params.get("symbol", "SPY")
        rsi_now = data["rsi"].iloc[-1]
        rsi_prev = data["rsi"].iloc[-2]
        if pd.isna(rsi_now):
            return None

        direction = None
        if rsi_prev < self.oversold <= rsi_now:
            direction = Direction.LONG
        elif rsi_prev > self.overbought >= rsi_now:
            direction = Direction.SHORT
        if direction is None:
            return None

        entry = self.get_entry(data)
        if entry is None:
            return None
        stop = self.get_stop_loss(entry, data, direction)
        target = self.get_take_profit(entry, data, direction)
        confidence = min(0.9, abs(50 - rsi_now) / 50)

        return TradeSignal(
            symbol=symbol,
            asset_class=self.params.get("asset_class", "STK"),
            timeframe=self.params.get("timeframe", "1 day"),
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=round(stop, 4),
            take_profit=round(target, 4),
            confidence_score=float(confidence),
            reason=f"RSI mean reversion at {rsi_now:.1f}",
            strategy_name=self.name,
        )
