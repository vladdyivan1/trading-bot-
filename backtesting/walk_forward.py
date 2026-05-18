"""Walk-forward validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from backtesting.engine import BacktestEngine, BacktestResult
from strategies.base_strategy import BaseStrategy


@dataclass
class WalkForwardSplit:
    train: pd.DataFrame
    test: pd.DataFrame


def rolling_splits(data: pd.DataFrame, train_size: int, test_size: int, step_size: int | None = None) -> list[WalkForwardSplit]:
    """Create chronological walk-forward splits."""

    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    step = step_size or test_size
    splits: list[WalkForwardSplit] = []
    start = 0
    while start + train_size + test_size <= len(data):
        train = data.iloc[start : start + train_size]
        test = data.iloc[start + train_size : start + train_size + test_size]
        splits.append(WalkForwardSplit(train=train, test=test))
        start += step
    return splits


def run_walk_forward(
    data: pd.DataFrame,
    strategy_factory: Callable[[pd.DataFrame], BaseStrategy],
    train_size: int,
    test_size: int,
    engine: BacktestEngine | None = None,
) -> list[BacktestResult]:
    """Train/tune strategy on each train split, then backtest on following test split."""

    bt_engine = engine or BacktestEngine()
    results: list[BacktestResult] = []
    for split in rolling_splits(data, train_size=train_size, test_size=test_size):
        strategy = strategy_factory(split.train)
        results.append(bt_engine.run(split.test, strategy))
    return results
