"""Feature engineering from OHLCV data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI, MACD, MAs, ATR, volume, volatility, trend features."""
    out = df.copy()
    close = out["close"]

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    out["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, 1e-10)))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]

    # Moving averages
    out["sma_10"] = close.rolling(10).mean()
    out["sma_20"] = close.rolling(20).mean()
    out["sma_50"] = close.rolling(50).mean()
    out["ema_20"] = close.ewm(span=20).mean()

    # ATR
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - close.shift()).abs(),
            (out["low"] - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(14).mean()
    out["atr_pct"] = out["atr"] / close

    # Volume
    out["volume_change"] = out["volume"].pct_change()
    out["volume_sma_ratio"] = out["volume"] / out["volume"].rolling(20).mean()

    # Volatility
    out["returns"] = close.pct_change()
    out["volatility_20"] = out["returns"].rolling(20).std()
    out["volatility_5"] = out["returns"].rolling(5).std()

    # Trend strength (ADX simplified)
    out["trend_strength"] = (out["sma_10"] - out["sma_50"]).abs() / close

    # Candle patterns
    body = close - out["open"]
    range_ = out["high"] - out["low"]
    out["body_pct"] = body / range_.replace(0, 1e-10)
    out["upper_wick"] = (out["high"] - pd.concat([close, out["open"]], axis=1).max(axis=1)) / range_.replace(
        0, 1e-10
    )
    out["lower_wick"] = (pd.concat([close, out["open"]], axis=1).min(axis=1) - out["low"]) / range_.replace(
        0, 1e-10
    )

    # Lag features (no lookahead — shifted forward for target alignment)
    for col in ["rsi", "macd_hist", "returns", "volatility_20"]:
        if col in out.columns:
            out[f"{col}_lag1"] = out[col].shift(1)
            out[f"{col}_lag2"] = out[col].shift(2)

    return out


def create_target(df: pd.DataFrame, horizon: int = 1) -> pd.Series:
    """Next-period direction: 1 if up, 0 if down."""
    future_return = df["close"].shift(-horizon) / df["close"] - 1
    return (future_return > 0).astype(int)


FEATURE_COLUMNS = [
    "rsi", "macd", "macd_hist", "sma_10", "sma_20", "sma_50",
    "ema_20", "atr_pct", "volume_change", "volume_sma_ratio",
    "volatility_20", "volatility_5", "trend_strength",
    "body_pct", "upper_wick", "lower_wick",
    "rsi_lag1", "macd_hist_lag1", "returns_lag1",
]
