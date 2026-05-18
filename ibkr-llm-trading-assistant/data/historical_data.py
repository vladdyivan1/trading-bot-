"""Historical data download and validation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from broker.ibkr_client import IBKRClient
from data.data_store import DataStore
from schemas import AssetClass


class HistoricalDataEngine:
    """Pull, validate, and cache historical OHLCV data."""

    MAX_YEARS = 5
    SUPPORTED_TIMEFRAMES = ["1 min", "5 mins", "15 mins", "1 hour", "1 day"]

    def __init__(self, client: Optional[IBKRClient] = None, store: Optional[DataStore] = None):
        self.client = client or IBKRClient()
        self.store = store or DataStore()

    def download(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str,
        use_cache: bool = True,
        force_refresh: bool = False,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> pd.DataFrame:
        """Download or load cached historical data."""
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        ac = asset_class.value
        if use_cache and not force_refresh and self.store.has_data(symbol, ac, timeframe):
            df = self.store.load(symbol, ac, timeframe)
            logger.info("Loaded {} cached bars for {}", len(df), symbol)
            return df

        if not self.client.is_connected:
            if not self.client.connect():
                raise ConnectionError("Cannot connect to IBKR for historical data")

        df = self._fetch_with_chunking(symbol, asset_class, timeframe, exchange, currency)
        if not df.empty:
            df = self.validate_bars(df, timeframe)
            self.store.save(df, symbol, ac, timeframe, exchange, currency)
        return df

    def _fetch_with_chunking(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str,
        exchange: str,
        currency: str,
    ) -> pd.DataFrame:
        """Fetch up to MAX_YEARS of data using IBKR duration limits."""
        duration_map = {
            "1 min": "1 D",
            "5 mins": "1 W",
            "15 mins": "2 W",
            "1 hour": "1 M",
            "1 day": "5 Y",
        }
        duration = duration_map.get(timeframe, "1 Y")
        df = self.client.get_historical_bars(
            symbol, asset_class, timeframe, duration=duration,
            exchange=exchange, currency=currency,
        )
        return df

    @staticmethod
    def validate_bars(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Detect and log missing candles."""
        if df.empty or len(df) < 2:
            return df

        freq_map = {
            "1 min": "1min",
            "5 mins": "5min",
            "15 mins": "15min",
            "1 hour": "1h",
            "1 day": "1D",
        }
        freq = freq_map.get(timeframe)
        if not freq:
            return df

        df = df.sort_index()
        expected = pd.date_range(df.index.min(), df.index.max(), freq=freq)
        missing = expected.difference(df.index)
        if len(missing) > 0:
            logger.warning(
                "Missing {} candles for timeframe {} ({} gaps)",
                len(missing),
                timeframe,
                len(missing),
            )
        return df

    def reload(self, symbol: str, asset_class: str, timeframe: str) -> pd.DataFrame:
        return self.store.load(symbol, asset_class, timeframe)
