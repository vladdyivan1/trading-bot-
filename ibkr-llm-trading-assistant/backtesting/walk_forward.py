"""Walk-forward validation for strategies and models."""

from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestEngine, BacktestResult
from strategies.base_strategy import BaseStrategy


class WalkForwardValidator:
    """Split data into train/test windows and aggregate metrics."""

    def __init__(
        self,
        train_bars: int = 252,
        test_bars: int = 63,
        step_bars: int | None = None,
    ) -> None:
        self.train_bars = train_bars
        self.test_bars = test_bars
        self.step_bars = step_bars or test_bars
        self.engine = BacktestEngine()

    def run(self, strategy: BaseStrategy, df: pd.DataFrame, symbol: str = "SPY") -> list[BacktestResult]:
        results: list[BacktestResult] = []
        start = 0
        n = len(df)
        while start + self.train_bars + self.test_bars <= n:
            test_start = start + self.train_bars
            test_end = test_start + self.test_bars
            test_df = df.iloc[test_start:test_end]
            result = self.engine.run(strategy, test_df, symbol)
            results.append(result)
            start += self.step_bars
        return results

    def aggregate(self, results: list[BacktestResult]) -> dict:
        if not results:
            return {}
        return {
            "folds": len(results),
            "avg_return": sum(r.metrics.total_return for r in results) / len(results),
            "avg_sharpe": sum(r.metrics.sharpe_ratio for r in results) / len(results),
            "avg_win_rate": sum(r.metrics.win_rate for r in results) / len(results),
            "total_trades": sum(r.metrics.num_trades for r in results),
        }
