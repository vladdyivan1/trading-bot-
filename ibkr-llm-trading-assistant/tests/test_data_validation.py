"""Tests for historical data validation."""

from datetime import datetime

import numpy as np
import pandas as pd

from data.historical_data import HistoricalDataEngine


def test_validate_bars_empty():
    df = pd.DataFrame()
    result = HistoricalDataEngine.validate_bars(df, "5 mins")
    assert result.empty


def test_validate_bars_returns_sorted():
    dates = pd.date_range("2024-01-01", periods=50, freq="5min")
    close = 100 + np.random.randn(50)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000,
        },
        index=dates,
    )
    result = HistoricalDataEngine.validate_bars(df, "5 mins")
    assert result.index.is_monotonic_increasing
