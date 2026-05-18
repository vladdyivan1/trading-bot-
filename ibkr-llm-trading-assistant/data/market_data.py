"""Live market data helpers (snapshot / streaming placeholder)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from broker.ibkr_client import IBKRClient


class MarketDataService:
    """Fetch latest quotes and build summaries for LLM analysis."""

    def __init__(self, client: IBKRClient) -> None:
        self.client = client

    def get_latest_price(self, contract) -> float | None:
        if not self.client.is_connected:
            return None
        tickers = self.client.ib.reqTickers(contract)
        if tickers:
            t = tickers[0]
            return t.marketPrice() or t.last or t.close
        return None

    def summarize_bars(self, df: pd.DataFrame, lookback: int = 20) -> dict:
        """Build a compact market summary for LLM input."""
        if df.empty:
            return {}
        tail = df.tail(lookback)
        close = tail["close"] if "close" in tail.columns else tail["Close"]
        return {
            "last_close": float(close.iloc[-1]),
            "high_20": float(close.max()),
            "low_20": float(close.min()),
            "return_20d_pct": float((close.iloc[-1] / close.iloc[0] - 1) * 100)
            if len(close) > 1
            else 0.0,
            "volatility_20d": float(close.pct_change().std() * (252**0.5))
            if len(close) > 2
            else 0.0,
            "bars": len(tail),
        }
