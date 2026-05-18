"""Feature engineering for predictive trading models."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base_strategy import average_true_range
from strategies.rsi_strategy import rsi


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def create_features(data: pd.DataFrame) -> pd.DataFrame:
    """Create features using only current and prior bars."""

    df = data.copy().sort_index()
    df["return_1"] = df["close"].pct_change()
    df["return_5"] = df["close"].pct_change(5)
    df["volatility_20"] = df["return_1"].rolling(20).std()
    df["sma_10"] = df["close"].rolling(10).mean()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["price_sma20_ratio"] = df["close"] / df["sma_20"] - 1
    df["sma10_sma50_ratio"] = df["sma_10"] / df["sma_50"] - 1
    df["rsi_14"] = rsi(df["close"], 14)
    macd_line, signal_line, hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist
    df["atr_14"] = average_true_range(df, 14)
    df["atr_pct"] = df["atr_14"] / df["close"]
    if "volume" in df:
        df["volume_change"] = df["volume"].pct_change()
        df["volume_zscore"] = (df["volume"] - df["volume"].rolling(20).mean()) / df["volume"].rolling(20).std()
    else:
        df["volume_change"] = 0.0
        df["volume_zscore"] = 0.0
    df["body_pct"] = (df["close"] - df["open"]) / df["open"]
    df["upper_wick_pct"] = (df["high"] - df[["open", "close"]].max(axis=1)) / df["open"]
    df["lower_wick_pct"] = (df[["open", "close"]].min(axis=1) - df["low"]) / df["open"]
    df["trend_strength"] = (df["sma_20"] - df["sma_50"]) / df["close"]
    return df.replace([np.inf, -np.inf], np.nan)


def make_supervised_dataset(data: pd.DataFrame, horizon: int = 1, target: str = "direction") -> tuple[pd.DataFrame, pd.Series]:
    """Return X/y where labels use future returns and features do not."""

    features = create_features(data)
    future_return = features["close"].pct_change(horizon).shift(-horizon)
    if target == "direction":
        y = (future_return > 0).astype(int)
    elif target == "return":
        y = future_return
    else:
        raise ValueError("target must be 'direction' or 'return'")
    X = features.drop(columns=[col for col in ["open", "high", "low", "close", "volume"] if col in features])
    dataset = X.join(y.rename("target")).dropna()
    return dataset.drop(columns=["target"]), dataset["target"]
