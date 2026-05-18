"""Real-time market data helpers (extension point)."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from broker.ibkr_client import IBKRClient
from schemas import AssetClass


class MarketDataService:
    """Snapshot and streaming market data (MVP: latest bar summary)."""

    def __init__(self, client: IBKRClient):
        self.client = client

    def get_latest_summary(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str = "5 mins",
    ) -> dict[str, Any]:
        """Return summary stats from most recent bars."""
        df = self.client.get_historical_bars(symbol, asset_class, timeframe, duration="1 D")
        if df.empty:
            return {"symbol": symbol, "error": "no data"}
        last = df.iloc[-1]
        return {
            "symbol": symbol,
            "last_close": float(last["close"]),
            "high": float(df["high"].max()),
            "low": float(df["low"].min()),
            "volume": float(df["volume"].sum()),
            "bars": len(df),
            "change_pct": float((last["close"] - df.iloc[0]["close"]) / df.iloc[0]["close"] * 100),
        }
