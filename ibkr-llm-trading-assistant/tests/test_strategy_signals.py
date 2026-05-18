"""Tests for strategy signal generation."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from schemas import Direction
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageCrossoverStrategy
from strategies.rsi_strategy import RSIMeanReversionStrategy
from strategies.strategy_registry import get_strategy, list_strategies


@pytest.fixture
def ohlcv_df():
    n = 100
    dates = pd.date_range(end=datetime.utcnow(), periods=n, freq="5min")
    close = 100 + np.cumsum(np.random.randn(n) * 0.2)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.random.randint(1000, 5000, n),
        },
        index=dates,
    )


def test_registry_lists_strategies():
    names = list_strategies()
    assert "ma_crossover" in names
    assert "rsi_mean_reversion" in names
    assert "breakout" in names


def test_get_strategy():
    s = get_strategy("ma_crossover", "SPY")
    assert s.symbol == "SPY"
    assert s.name == "ma_crossover"


def test_ma_indicators(ohlcv_df):
    strategy = MovingAverageCrossoverStrategy("SPY", fast_period=5, slow_period=10)
    enriched = strategy.calculate_indicators(ohlcv_df)
    assert "sma_fast" in enriched.columns
    assert "atr" in enriched.columns


def test_signal_structure_when_present(ohlcv_df):
    """If a signal is generated, it must have valid structure."""
    strategy = MovingAverageCrossoverStrategy("SPY", fast_period=3, slow_period=5)
    signal = strategy.run(ohlcv_df)
    if signal:
        assert signal.symbol == "SPY"
        assert signal.direction in (Direction.LONG, Direction.SHORT)
        assert 0 <= signal.confidence_score <= 1
        assert signal.reward_to_risk >= 0


def test_rsi_strategy_runs(ohlcv_df):
    strategy = RSIMeanReversionStrategy("SPY")
    enriched = strategy.calculate_indicators(ohlcv_df)
    assert "rsi" in enriched.columns


def test_breakout_strategy_runs(ohlcv_df):
    strategy = BreakoutStrategy("SPY", lookback=10)
    enriched = strategy.calculate_indicators(ohlcv_df)
    assert "high_n" in enriched.columns


def test_insufficient_data_returns_none():
    strategy = MovingAverageCrossoverStrategy("SPY")
    small = pd.DataFrame(
        {"open": [1], "high": [1], "low": [1], "close": [1], "volume": [1]}
    )
    assert strategy.run(small) is None
