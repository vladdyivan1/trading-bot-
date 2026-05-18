"""Feature engineering from OHLCV data."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    mapping = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    for old, new in mapping.items():
        if old in out.columns and new not in out.columns:
            out[new] = out[old]
    return out


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return line, sig, hist


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create ML features without lookahead (shift targets separately)."""
    data = _ensure_ohlcv(df)
    close = data["close"]
    vol = data.get("volume", pd.Series(0, index=data.index))

    features = pd.DataFrame(index=data.index)
    features["return_1"] = close.pct_change(1)
    features["return_5"] = close.pct_change(5)
    features["rsi_14"] = rsi(close, 14)
    macd_line, macd_sig, macd_hist = macd(close)
    features["macd"] = macd_line
    features["macd_signal"] = macd_sig
    features["macd_hist"] = macd_hist
    features["sma_10"] = close.rolling(10).mean() / close - 1
    features["sma_50"] = close.rolling(50).mean() / close - 1
    features["atr_pct"] = atr(data, 14) / close
    features["vol_change"] = vol.pct_change(5)
    features["volatility_20"] = close.pct_change().rolling(20).std()
    features["trend_strength"] = (close - close.rolling(20).mean()) / close.rolling(20).std().replace(0, np.nan)
    features["body_pct"] = (close - data["open"]) / data["open"]
    features["range_pct"] = (data["high"] - data["low"]) / close

    return features.dropna()
