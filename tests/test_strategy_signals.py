from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy


def make_uptrend_bars(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = np.linspace(100, 130, n)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.linspace(1000, 5000, n),
        },
        index=idx,
    )


def make_downtrend_bars(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2022-01-01", periods=n, freq="D")
    close = np.linspace(130, 100, n)
    return pd.DataFrame(
        {
            "open": close + 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.linspace(5000, 1000, n),
        },
        index=idx,
    )


def test_moving_average_strategy_signal_shape():
    bars = make_uptrend_bars()
    strategy = MovingAverageStrategy(fast_window=5, slow_window=20)
    signal = strategy.generate_signal(bars, symbol="SPY", asset_class="STK", timeframe="1 day")
    if signal is not None:
        assert signal.symbol == "SPY"
        assert signal.direction in {"long", "short"}
        assert 0 <= signal.confidence_score <= 1


def test_rsi_strategy_signal_shape():
    bars = make_downtrend_bars()
    strategy = RSIStrategy(rsi_window=7)
    signal = strategy.generate_signal(bars, symbol="SPY", asset_class="STK", timeframe="1 day")
    if signal is not None:
        assert signal.strategy_name == "rsi_mean_reversion"
        assert signal.entry_price > 0


def test_breakout_strategy_signal_shape():
    bars = make_uptrend_bars()
    bars.iloc[-1, bars.columns.get_loc("close")] = bars["high"].iloc[:-1].max() + 3
    bars.iloc[-1, bars.columns.get_loc("volume")] = bars["volume"].rolling(20).mean().iloc[-1] * 2
    strategy = BreakoutStrategy(lookback=20)
    signal = strategy.generate_signal(bars, symbol="SPY", asset_class="STK", timeframe="1 day")
    assert signal is not None
    assert signal.direction == "long"
    assert signal.reason
