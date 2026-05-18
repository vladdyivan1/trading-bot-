"""SQLite persistence for market data."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from loguru import logger

from database.db import get_db_session
from database.repositories import CandleRepository


class DataStore:
    """Persist and reload candle data from SQLite."""

    def save(
        self,
        df: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> int:
        if df.empty:
            return 0
        with get_db_session() as session:
            repo = CandleRepository(session)
            count = repo.save_bars(df, symbol, asset_class, timeframe, exchange, currency)
            logger.info("Saved {} bars for {} {} {}", count, symbol, asset_class, timeframe)
            return count

    def load(
        self,
        symbol: str,
        asset_class: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        with get_db_session() as session:
            repo = CandleRepository(session)
            return repo.load_bars(symbol, asset_class, timeframe, start, end)

    def has_data(self, symbol: str, asset_class: str, timeframe: str) -> bool:
        df = self.load(symbol, asset_class, timeframe)
        return not df.empty
