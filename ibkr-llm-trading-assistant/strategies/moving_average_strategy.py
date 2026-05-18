"""Moving average crossover strategy."""

from __future__ import annotations

import pandas as pd

from schemas import Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    name = "moving_average_crossover"

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params)
        self.fast = int(self.params.get("fast_period", 10))
        self.slow = int(self.params.get("slow_period", 30))

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = out["close"] if "close" in out.columns else out["Close"]
        out["sma_fast"] = close.rolling(self.fast).mean()
        out["sma_slow"] = close.rolling(self.slow).mean()
        out["ma_cross"] = (out["sma_fast"] > out["sma_slow"]).astype(int)
        return out

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal | None:
        if len(df) < self.slow + 2:
            return None
        data = self.calculate_indicators(df)
        symbol = str(data.get("symbol", pd.Series(["SPY"])).iloc[-1] if "symbol" in data.columns else self.params.get("symbol", "SPY"))
        if "symbol" in data.columns:
            symbol = str(data["symbol"].iloc[-1])

        prev_cross = data["ma_cross"].iloc[-2]
        curr_cross = data["ma_cross"].iloc[-1]
        if prev_cross == 0 and curr_cross == 1:
            direction = Direction.LONG
        elif prev_cross == 1 and curr_cross == 0:
            direction = Direction.SHORT
        else:
            return None

        entry = self.get_entry(data)
        if entry is None:
            return None
        stop = self.get_stop_loss(entry, data, direction)
        target = self.get_take_profit(entry, data, direction)
        spread = abs(entry - stop) / entry if entry else 0
        confidence = min(0.85, 0.55 + spread * 10)

        return TradeSignal(
            symbol=symbol,
            asset_class=self.params.get("asset_class", "STK"),
            timeframe=self.params.get("timeframe", "1 day"),
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=round(stop, 4),
            take_profit=round(target, 4),
            confidence_score=confidence,
            reason=f"SMA{self.fast}/{self.slow} crossover",
            strategy_name=self.name,
        )
