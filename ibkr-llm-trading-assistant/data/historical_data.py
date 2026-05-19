"""Historical data download and validation."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from broker.ibkr_client import IBKRClient
from broker.contracts import build_contract
from data.data_store import DataStore

# IBKR duration limits vary by bar size; map timeframe to bar_size and max duration chunks
TIMEFRAME_MAP = {
    "1 min": ("1 min", "1 M"),
    "5 mins": ("5 mins", "1 M"),
    "15 mins": ("15 mins", "1 M"),
    "1 hour": ("1 hour", "1 Y"),
    "1 day": ("1 day", "5 Y"),
}

MAX_YEARS = 5


class HistoricalDataService:
    """Pull and persist historical OHLCV data."""

    def __init__(self, client: IBKRClient | None = None, store: DataStore | None = None) -> None:
        self.client = client or IBKRClient()
        self.store = store or DataStore()

    def download(
        self,
        symbol: str,
        timeframe: str = "1 day",
        asset_class: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        years: int = 5,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Download historical data, using cache when available."""
        years = min(years, MAX_YEARS)
        if not force_refresh:
            cached = self.store.load(symbol, timeframe, asset_class)
            if not cached.empty and len(cached) > 50:
                logger.info("Loaded {} bars from cache for {}", len(cached), symbol)
                return cached

        if not self.client.is_connected and not self.client.connect():
            logger.warning("IBKR not connected; returning cached data only")
            return self.store.load(symbol, timeframe, asset_class)

        bar_size, duration = TIMEFRAME_MAP.get(timeframe, ("1 day", "5 Y"))
        contract = build_contract(symbol, asset_class, exchange, currency)

        try:
            qualified = self.client.ib.qualifyContracts(contract)
            if not qualified:
                raise ValueError(f"Could not qualify {symbol}")
            contract = qualified[0]
        except Exception as exc:
            logger.error("Contract qualification failed: {}", exc)
            return self.store.load(symbol, timeframe, asset_class)

        all_frames: list[pd.DataFrame] = []
        # For daily data, single pull; for intraday, chunk by month
        if bar_size == "1 day":
            df = self.client.get_historical_bars(
                contract, duration=f"{years} Y", bar_size=bar_size
            )
            if not df.empty:
                all_frames.append(df)
        else:
            months = years * 12
            for i in range(months):
                end = datetime.utcnow() - timedelta(days=30 * i)
                df = self.client.get_historical_bars(
                    contract,
                    duration="1 M",
                    bar_size=bar_size,
                )
                if df.empty:
                    break
                all_frames.append(df)

        if not all_frames:
            return pd.DataFrame()

        combined = pd.concat(all_frames)
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index()
        combined = self._normalize_df(combined, symbol, asset_class, exchange, currency, timeframe)
        self.store.save(combined)
        gaps = self.validate_gaps(combined, timeframe)
        if gaps:
            logger.warning("Found {} gap(s) in {}", len(gaps), symbol)
        return combined

    def _normalize_df(
        self,
        df: pd.DataFrame,
        symbol: str,
        asset_class: str,
        exchange: str,
        currency: str,
        timeframe: str,
    ) -> pd.DataFrame:
        df = df.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            time_col = df.columns[0]
            df = df.rename(columns={time_col: "bar_time"})
        df["symbol"] = symbol
        df["asset_class"] = asset_class
        df["exchange"] = exchange
        df["currency"] = currency
        df["timeframe"] = timeframe
        for col in ("open", "high", "low", "close", "volume"):
            if col not in df.columns and col.capitalize() in df.columns:
                df[col] = df[col.capitalize()]
        return df.set_index("bar_time")

    def validate_gaps(self, df: pd.DataFrame, timeframe: str) -> list[tuple]:
        """Detect missing candles based on expected frequency."""
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            if "bar_time" in df.columns:
                times = pd.to_datetime(df["bar_time"])
            else:
                return []
        else:
            times = df.index

        freq_map = {
            "1 min": "1min",
            "5 mins": "5min",
            "15 mins": "15min",
            "1 hour": "1h",
            "1 day": "1D",
        }
        freq = freq_map.get(timeframe, "1D")
        expected = pd.date_range(times.min(), times.max(), freq=freq)
        missing = expected.difference(times)
        return [(m,) for m in missing[:100]]
