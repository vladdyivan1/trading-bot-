"""Donchian channel breakout strategy."""

from __future__ import annotations

import pandas as pd

from schemas import Direction, TradeSignal
from strategies.base_strategy import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    name = "breakout"

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params)
        self.lookback = int(self.params.get("lookback", 20))

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        high = out["high"] if "high" in out.columns else out["High"]
        low = out["low"] if "low" in out.columns else out["Low"]
        close = out["close"] if "close" in out.columns else out["Close"]
        out["upper_band"] = high.rolling(self.lookback).max()
        out["lower_band"] = low.rolling(self.lookback).min()
        vol = out["volume"] if "volume" in out.columns else pd.Series(1, index=out.index)
        out["vol_ma"] = vol.rolling(self.lookback).mean()
        out["vol_ratio"] = vol / out["vol_ma"].replace(0, 1)
        out["close"] = close
        return out

    def generate_signal(self, df: pd.DataFrame) -> TradeSignal | None:
        if len(df) < self.lookback + 2:
            return None
        data = self.calculate_indicators(df)
        symbol = str(data["symbol"].iloc[-1]) if "symbol" in data.columns else self.params.get("symbol", "SPY")
        close = data["close"].iloc[-1]
        prev_close = data["close"].iloc[-2]
        upper = data["upper_band"].iloc[-2]
        lower = data["lower_band"].iloc[-2]
        vol_ok = data["vol_ratio"].iloc[-1] > 1.0

        direction = None
        if prev_close <= upper < close and vol_ok:
            direction = Direction.LONG
        elif prev_close >= lower > close and vol_ok:
            direction = Direction.SHORT
        if direction is None:
            return None

        entry = float(close)
        stop = self.get_stop_loss(entry, data, direction)
        target = self.get_take_profit(entry, data, direction)

        return TradeSignal(
            symbol=symbol,
            asset_class=self.params.get("asset_class", "STK"),
            timeframe=self.params.get("timeframe", "1 day"),
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=round(stop, 4),
            take_profit=round(target, 4),
            confidence_score=0.72 if vol_ok else 0.6,
            reason="Trend breakout with volume confirmation",
            strategy_name=self.name,
        )
