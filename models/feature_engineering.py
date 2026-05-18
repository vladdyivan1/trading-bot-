"""Feature engineering for predictive models."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    avg_gain = up.rolling(window).mean()
    avg_loss = down.rolling(window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def build_features(bars: pd.DataFrame) -> pd.DataFrame:
    df = bars.copy().sort_index()
    df["return_1"] = df["close"].pct_change(1)
    df["return_5"] = df["close"].pct_change(5)
    df["volatility_20"] = df["return_1"].rolling(20).std()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["rsi_14"] = _rsi(df["close"], 14)
    macd, macd_signal = _macd(df["close"])
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    tr = np.maximum(df["high"] - df["low"], np.maximum(abs(df["high"] - df["close"].shift(1)), abs(df["low"] - df["close"].shift(1))))
    df["atr_14"] = tr.rolling(14).mean()
    df["volume_change"] = df["volume"].pct_change().replace([np.inf, -np.inf], 0)
    df["trend_strength"] = (df["ema_20"] - df["sma_50"]) / df["close"].replace(0, np.nan)

    # Candle pattern proxies
    body = (df["close"] - df["open"]).abs()
    range_ = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_to_range"] = body / range_
    df["bullish_candle"] = (df["close"] > df["open"]).astype(float)

    return df


def make_training_set(bars: pd.DataFrame, horizon: int = 1) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    df = build_features(bars)
    df["target_return"] = df["close"].pct_change(horizon).shift(-horizon)
    df["target_direction"] = (df["target_return"] > 0).astype(int)

    feature_cols = [
        "return_1",
        "return_5",
        "volatility_20",
        "sma_20",
        "sma_50",
        "ema_20",
        "rsi_14",
        "macd",
        "macd_signal",
        "atr_14",
        "volume_change",
        "trend_strength",
        "body_to_range",
        "bullish_candle",
    ]
    dataset = df.dropna(subset=feature_cols + ["target_direction"])
    X = dataset[feature_cols]
    y = dataset["target_direction"].astype(int)
    return X, y, feature_cols
