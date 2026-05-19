"""Backtest engine and metrics tests."""

import pandas as pd

from backtesting.engine import BacktestEngine
from backtesting.metrics import compute_metrics
from strategies.moving_average_strategy import MovingAverageStrategy


def test_backtest_runs(sample_ohlcv: pd.DataFrame) -> None:
    strategy = MovingAverageStrategy({"symbol": "TEST", "fast_period": 5, "slow_period": 20})
    engine = BacktestEngine()
    result = engine.run(strategy, sample_ohlcv, "TEST")
    assert result.metrics.num_trades >= 0
    assert len(result.equity_curve) > 0


def test_metrics_empty_trades() -> None:
    m = compute_metrics(pd.DataFrame(), pd.Series([100_000, 100_000]))
    assert m.num_trades == 0


def test_metrics_with_trades() -> None:
    trades = pd.DataFrame({"pnl": [100, -50, 200, -30], "hold_bars": [5, 3, 10, 2]})
    equity = pd.Series([100_000, 100_100, 100_050, 100_250, 100_220])
    m = compute_metrics(trades, equity)
    assert m.num_trades == 4
    assert m.win_rate == 0.5
    assert m.expectancy != 0
