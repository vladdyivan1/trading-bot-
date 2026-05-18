"""Historical data service backed by IBKR and SQLite cache."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from data.data_store import HistoricalDataStore


IBKR_BAR_SIZES = {
    "1 min": "1 min",
    "5 mins": "5 mins",
    "15 mins": "15 mins",
    "1 hour": "1 hour",
    "1 day": "1 day",
}


class HistoricalDataService:
    """Fetch historical data from IBKR only when local cache is empty."""

    def __init__(self, ibkr_client: object, store: HistoricalDataStore | None = None) -> None:
        self.ibkr_client = ibkr_client
        self.store = store or HistoricalDataStore()

    def get_or_fetch(
        self,
        symbol: str,
        asset_class: str,
        timeframe: str,
        duration: str = "5 Y",
        exchange: str = "SMART",
        currency: str = "USD",
        end_datetime: datetime | None = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """Load stored bars or fetch from IBKR and cache them."""

        if timeframe not in IBKR_BAR_SIZES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        if not force_refresh:
            stored = self.store.load_bars(symbol, asset_class, exchange, currency, timeframe)
            if not stored.empty:
                return stored

        fetch = getattr(self.ibkr_client, "fetch_historical_bars")
        bars = fetch(
            symbol=symbol,
            asset_class=asset_class,
            exchange=exchange,
            currency=currency,
            duration=duration,
            bar_size=IBKR_BAR_SIZES[timeframe],
            end_datetime=end_datetime,
        )
        self.store.save_bars(bars, symbol, asset_class, timeframe, exchange, currency)
        return self.store.load_bars(symbol, asset_class, exchange, currency, timeframe)
