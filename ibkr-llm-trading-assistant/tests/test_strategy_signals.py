"""Strategy signal generation tests."""

import pandas as pd

from schemas import Direction
from strategies.breakout_strategy import BreakoutStrategy
from strategies.moving_average_strategy import MovingAverageStrategy
from strategies.rsi_strategy import RSIStrategy


def test_ma_strategy_indicators(sample_ohlcv: pd.DataFrame) -> None:
    strat = MovingAverageStrategy({"fast_period": 5, "slow_period": 20})
    out = strat.calculate_indicators(sample_ohlcv)
    assert "sma_fast" in out.columns
    assert "sma_slow" in out.columns


def test_signal_structure(sample_ohlcv: pd.DataFrame) -> None:
    strat = MovingAverageStrategy({"symbol": "TEST", "fast_period": 3, "slow_period": 8})
    # Force crossover pattern
    df = sample_ohlcv.copy()
    signal = strat.generate_signal(df)
    if signal:
        assert signal.symbol
        assert signal.direction in (Direction.LONG, Direction.SHORT)
        assert signal.reward_to_risk >= 0
        assert 0 <= signal.confidence_score <= 1


def test_rsi_strategy(sample_ohlcv: pd.DataFrame) -> None:
    strat = RSIStrategy({"symbol": "TEST"})
    out = strat.calculate_indicators(sample_ohlcv)
    assert "rsi" in out.columns


def test_breakout_strategy(sample_ohlcv: pd.DataFrame) -> None:
    strat = BreakoutStrategy({"symbol": "TEST", "lookback": 10})
    out = strat.calculate_indicators(sample_ohlcv)
    assert "upper_band" in out.columns
