"""Walk-forward backtesting utilities."""

from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


def walk_forward_splits(
    bars: pd.DataFrame,
    train_size: int,
    test_size: int,
    step_size: int,
):
    total = len(bars)
    start = 0
    while start + train_size + test_size <= total:
        train = bars.iloc[start : start + train_size]
        test = bars.iloc[start + train_size : start + train_size + test_size]
        yield train, test
        start += step_size


class WalkForwardEngine:
    """Run repeated out-of-sample tests for a strategy factory."""

    def __init__(self, backtest_engine: BacktestEngine | None = None) -> None:
        self.backtest_engine = backtest_engine or BacktestEngine()

    def run(
        self,
        strategy: BaseStrategy,
        bars: pd.DataFrame,
        symbol: str,
        asset_class: str,
        timeframe: str,
        train_size: int = 300,
        test_size: int = 100,
        step_size: int = 100,
    ) -> pd.DataFrame:
        rows = []
        for fold, (_, test) in enumerate(walk_forward_splits(bars, train_size, test_size, step_size), start=1):
            result = self.backtest_engine.run(strategy, test, symbol=symbol, asset_class=asset_class, timeframe=timeframe)
            rows.append({"fold": fold, **result.metrics})
        return pd.DataFrame(rows)
