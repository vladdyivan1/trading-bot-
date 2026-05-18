"""Historical data pull orchestration with IBKR and SQLite caching."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from broker.contracts import ContractSpec
from broker.ibkr_client import IBKRClient
from data.data_store import DataStore

BAR_SIZE_MAP = {
    "1 min": "1 min",
    "5 mins": "5 mins",
    "15 mins": "15 mins",
    "1 hour": "1 hour",
    "1 day": "1 day",
}


class HistoricalDataEngine:
    """Download and cache market history with validation."""

    def __init__(self, ibkr_client: IBKRClient, data_store: DataStore | None = None) -> None:
        self.ibkr_client = ibkr_client
        self.data_store = data_store or DataStore()

    def load_or_fetch(
        self,
        contract: ContractSpec,
        timeframe: str,
        years: int = 5,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        existing = self.data_store.load_dataframe(
            symbol=contract.symbol,
            asset_class=contract.asset_class,
            exchange=contract.exchange,
            currency=contract.currency,
            timeframe=timeframe,
        )
        if not force_refresh and not existing.empty:
            return existing

        bars = self.fetch_from_ibkr(contract, timeframe=timeframe, years=years)
        self.data_store.save_dataframe(
            symbol=contract.symbol,
            asset_class=contract.asset_class,
            exchange=contract.exchange,
            currency=contract.currency,
            timeframe=timeframe,
            bars=bars,
        )
        return bars

    def fetch_from_ibkr(self, contract: ContractSpec, timeframe: str, years: int = 5) -> pd.DataFrame:
        if timeframe not in BAR_SIZE_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        duration = f"{years} Y"
        what_to_show = "MIDPOINT" if contract.asset_class == "FX" else "TRADES"
        bars = self.ibkr_client.req_historical_data(
            spec=contract,
            end_datetime=datetime.utcnow(),
            duration=duration,
            bar_size=BAR_SIZE_MAP[timeframe],
            what_to_show=what_to_show,
            use_rth=contract.asset_class in {"STK", "ETF"},
        )
        if bars.empty:
            return bars

        bars = bars.sort_index()
        bars.index = pd.to_datetime(bars.index).tz_localize(None)
        cutoff = datetime.utcnow() - timedelta(days=365 * years)
        bars = bars[bars.index >= cutoff]
        return bars

    def validate(self, bars: pd.DataFrame, timeframe: str) -> dict:
        return self.data_store.validate_dataset(bars, timeframe=timeframe)
