"""SQLite-backed OHLCV storage."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from database.db import get_session
from database.repositories import OHLCVRepository


class DataStore:
    """Persist and reload OHLCV bars from SQLite."""

    def save(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        records_df = df.reset_index() if isinstance(df.index, pd.DatetimeIndex) else df.copy()
        if "bar_time" not in records_df.columns:
            records_df = records_df.rename(columns={records_df.columns[0]: "bar_time"})
        records_df["bar_time"] = pd.to_datetime(records_df["bar_time"])
        cols = [
            "symbol",
            "asset_class",
            "exchange",
            "currency",
            "timeframe",
            "bar_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        for c in cols:
            if c not in records_df.columns:
                if c == "volume":
                    records_df[c] = 0.0
                elif c == "exchange":
                    records_df[c] = "SMART"
                elif c == "currency":
                    records_df[c] = "USD"
        payload = records_df[cols].to_dict(orient="records")
        with get_session() as session:
            repo = OHLCVRepository(session)
            return repo.upsert_bars(pd.DataFrame(payload))

    def load(
        self,
        symbol: str,
        timeframe: str,
        asset_class: str = "STK",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        with get_session() as session:
            repo = OHLCVRepository(session)
            return repo.load_bars(symbol, timeframe, asset_class, start, end)
