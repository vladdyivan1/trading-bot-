"""Pytest configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Synthetic trending OHLCV data for tests."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    price = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame(
        {
            "open": price - 0.2,
            "high": price + 0.5,
            "low": price - 0.5,
            "close": price,
            "volume": np.random.randint(1_000_000, 5_000_000, n),
            "symbol": "TEST",
        },
        index=dates,
    )
    df.index.name = "bar_time"
    return df
