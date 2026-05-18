"""Market data summarization helpers for AI context."""

from __future__ import annotations

import pandas as pd


def summarize_market_data(bars: pd.DataFrame) -> dict:
    if bars.empty:
        return {
            "rows": 0,
            "trend": "unknown",
            "volatility": None,
            "last_close": None,
        }

    close = bars["close"].astype(float)
    returns = close.pct_change().dropna()
    trend = "up" if close.iloc[-1] > close.iloc[max(0, len(close) - 20)] else "down"
    return {
        "rows": int(len(bars)),
        "last_close": float(close.iloc[-1]),
        "return_1d_pct": float((close.iloc[-1] / close.iloc[-2] - 1.0) * 100) if len(close) > 1 else 0.0,
        "volatility_annualized": float(returns.std() * (252**0.5)) if not returns.empty else 0.0,
        "trend": trend,
        "avg_volume": float(bars["volume"].tail(20).mean()) if "volume" in bars.columns else 0.0,
    }
