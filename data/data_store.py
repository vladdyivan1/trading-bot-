"""SQLite-backed historical data storage."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import select

from database.db import get_session, init_db
from database.models import HistoricalBar


TIMEFRAME_TO_PANDAS_FREQ = {
    "1 min": "1min",
    "5 mins": "5min",
    "15 mins": "15min",
    "1 hour": "1h",
    "1 day": "1D",
}


class HistoricalDataStore:
    """Persist and reload historical OHLCV bars."""

    def __init__(self) -> None:
        init_db()

    def save_bars(
        self,
        bars: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> int:
        """Save bars and return number of new rows inserted."""

        if bars.empty:
            return 0
        df = self._normalize_bars(bars)
        inserted = 0
        with get_session() as session:
            existing = session.execute(
                select(HistoricalBar.timestamp).where(
                    HistoricalBar.symbol == symbol,
                    HistoricalBar.asset_class == asset_class,
                    HistoricalBar.exchange == exchange,
                    HistoricalBar.currency == currency,
                    HistoricalBar.timeframe == timeframe,
                )
            ).scalars()
            existing_timestamps = set(existing)
            for timestamp, row in df.iterrows():
                ts = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
                if ts in existing_timestamps:
                    continue
                session.add(
                    HistoricalBar(
                        symbol=symbol,
                        asset_class=asset_class,
                        exchange=exchange,
                        currency=currency,
                        timeframe=timeframe,
                        timestamp=ts,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0.0) or 0.0),
                    )
                )
                inserted += 1
        return inserted

    def load_bars(
        self,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Load bars from SQLite as a datetime-indexed DataFrame."""

        with get_session() as session:
            stmt = select(HistoricalBar).where(
                HistoricalBar.symbol == symbol,
                HistoricalBar.asset_class == asset_class,
                HistoricalBar.exchange == exchange,
                HistoricalBar.currency == currency,
                HistoricalBar.timeframe == timeframe,
            )
            if start is not None:
                stmt = stmt.where(HistoricalBar.timestamp >= start)
            if end is not None:
                stmt = stmt.where(HistoricalBar.timestamp <= end)
            rows = session.execute(stmt.order_by(HistoricalBar.timestamp)).scalars().all()

        records = [
            {
                "timestamp": row.timestamp,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }
            for row in rows
        ]
        if not records:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(records).set_index("timestamp")
        df.index = pd.to_datetime(df.index)
        return df.sort_index()

    def validate_missing_candles(self, bars: pd.DataFrame, timeframe: str) -> pd.DatetimeIndex:
        """Return expected timestamps missing from a candle series."""

        if bars.empty:
            return pd.DatetimeIndex([])
        if timeframe not in TIMEFRAME_TO_PANDAS_FREQ:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        df = self._normalize_bars(bars)
        expected = pd.date_range(df.index.min(), df.index.max(), freq=TIMEFRAME_TO_PANDAS_FREQ[timeframe])
        return expected.difference(df.index)

    def _normalize_bars(self, bars: pd.DataFrame) -> pd.DataFrame:
        df = bars.copy()
        if "date" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        df.index = pd.to_datetime(df.index)
        lower_columns = {col: col.lower() for col in df.columns}
        df = df.rename(columns=lower_columns)
        for col in ["open", "high", "low", "close"]:
            if col not in df.columns:
                raise ValueError(f"Missing required OHLC column: {col}")
        if "volume" not in df.columns:
            df["volume"] = 0.0
        return df[["open", "high", "low", "close", "volume"]].sort_index()
