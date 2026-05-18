"""Data persistence and validation services."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from database.repositories import HistoricalDataRepository

TIMEFRAME_TO_FREQ = {
    "1 min": "1min",
    "5 mins": "5min",
    "15 mins": "15min",
    "1 hour": "1H",
    "1 day": "1D",
}


class DataStore:
    """Store and validate market data in SQLite."""

    def __init__(self, repository: HistoricalDataRepository | None = None) -> None:
        self.repository = repository or HistoricalDataRepository()

    def save_dataframe(
        self,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
        bars: pd.DataFrame,
    ) -> int:
        bars = bars.copy()
        if not isinstance(bars.index, pd.DatetimeIndex):
            raise ValueError("bars index must be DatetimeIndex")
        if not {"open", "high", "low", "close"}.issubset(set(bars.columns)):
            raise ValueError("bars must contain open/high/low/close columns")
        if "volume" not in bars.columns:
            bars["volume"] = 0.0
        return self.repository.save_bars(symbol, asset_class, exchange, currency, timeframe, bars)

    def load_dataframe(
        self,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        return self.repository.load_bars(symbol, asset_class, exchange, currency, timeframe, start, end)

    def missing_candles(self, bars: pd.DataFrame, timeframe: str) -> list[pd.Timestamp]:
        if bars.empty:
            return []
        freq = TIMEFRAME_TO_FREQ.get(timeframe)
        if freq is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        ordered = bars.sort_index()
        expected = pd.date_range(start=ordered.index.min(), end=ordered.index.max(), freq=freq)
        missing = expected.difference(ordered.index)
        return list(missing)

    def validate_dataset(self, bars: pd.DataFrame, timeframe: str) -> dict:
        if bars.empty:
            return {"valid": False, "issues": ["empty dataset"]}

        issues: list[str] = []
        missing = self.missing_candles(bars, timeframe)
        if missing:
            issues.append(f"missing_candles={len(missing)}")

        if (bars[["open", "high", "low", "close"]] <= 0).any().any():
            issues.append("non_positive_price")

        if (bars["high"] < bars["low"]).any():
            issues.append("high_below_low")

        return {"valid": not issues, "issues": issues, "rows": int(len(bars))}
