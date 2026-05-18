"""Tests for backtesting engine and metrics."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics, _max_drawdown, _sharpe_ratio
from schemas import BacktestTrade, Direction
from strategies.moving_average_strategy import MovingAverageCrossoverStrategy


@pytest.fixture
def sample_ohlcv():
    """Generate trending OHLCV data for backtests."""
    n = 300
    dates = pd.date_range(end=datetime.utcnow(), periods=n, freq="5min")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.3)
    df = pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.random.randint(1000, 10000, n),
        },
        index=dates,
    )
    return df


def test_max_drawdown():
    equity = [100000, 105000, 102000, 98000, 103000]
    dd = _max_drawdown(equity)
    assert dd > 0
    assert dd < 10


def test_sharpe_ratio_zero_std():
    returns = pd.Series([0.01] * 10)
    assert _sharpe_ratio(returns) == 0.0


def test_compute_metrics_empty():
    result = compute_metrics([], [100000], 100000, "test", "SPY", "5 mins")
    assert result.num_trades == 0
    assert result.total_return == 0.0


def test_compute_metrics_with_trades():
    trades = [
        BacktestTrade(
            symbol="SPY",
            direction=Direction.LONG,
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            entry_price=100,
            exit_price=102,
            quantity=10,
            pnl=20,
            commission=1,
            slippage=0.5,
            strategy_name="test",
        ),
        BacktestTrade(
            symbol="SPY",
            direction=Direction.LONG,
            entry_time=datetime(2024, 1, 3),
            exit_time=datetime(2024, 1, 4),
            entry_price=102,
            exit_price=101,
            quantity=10,
            pnl=-10,
            commission=1,
            slippage=0.5,
            strategy_name="test",
        ),
    ]
    equity = [100000, 100020, 100010]
    result = compute_metrics(trades, equity, 100000, "test", "SPY", "5 mins")
    assert result.num_trades == 2
    assert 0 <= result.win_rate <= 100
    assert result.expectancy != 0 or result.num_trades > 0


def test_backtest_engine_runs(sample_ohlcv):
    strategy = MovingAverageCrossoverStrategy("SPY", fast_period=5, slow_period=15)
    engine = BacktestEngine(initial_capital=100000)
    result = engine.run(strategy, sample_ohlcv)
    assert result.strategy_name == "ma_crossover"
    assert len(result.equity_curve) > 1
    assert isinstance(result.max_drawdown, float)


def test_compare_strategies(sample_ohlcv):
    from strategies.rsi_strategy import RSIMeanReversionStrategy

    engine = BacktestEngine()
    s1 = MovingAverageCrossoverStrategy("SPY", fast_period=5, slow_period=15)
    s2 = RSIMeanReversionStrategy("SPY")
    results = engine.compare_strategies([s1, s2], sample_ohlcv)
    assert len(results) == 2
