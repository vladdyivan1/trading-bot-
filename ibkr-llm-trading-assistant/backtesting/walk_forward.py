"""Walk-forward validation to avoid overfitting."""

from __future__ import annotations

from typing import Any, Callable, List

import pandas as pd
from loguru import logger

from backtesting.engine import BacktestEngine
from schemas import BacktestResult
from strategies.base_strategy import BaseStrategy


class WalkForwardValidator:
    """Rolling train/test splits for parameter validation."""

    def __init__(
        self,
        train_bars: int = 500,
        test_bars: int = 100,
        step_bars: int = 100,
    ):
        self.train_bars = train_bars
        self.test_bars = test_bars
        self.step_bars = step_bars
        self.engine = BacktestEngine()

    def run(
        self,
        strategy_factory: Callable[..., BaseStrategy],
        df: pd.DataFrame,
        strategy_kwargs: dict | None = None,
    ) -> List[BacktestResult]:
        """Run walk-forward backtests on rolling windows."""
        kwargs = strategy_kwargs or {}
        results: List[BacktestResult] = []
        start = 0
        total = len(df)

        while start + self.train_bars + self.test_bars <= total:
            test_start = start + self.train_bars
            test_end = test_start + self.test_bars
            test_df = df.iloc[test_start:test_end]
            strategy = strategy_factory(**kwargs)
            result = self.engine.run(strategy, test_df)
            results.append(result)
            logger.info(
                "Walk-forward fold {}: {} trades, return {:.2f}%",
                len(results),
                result.num_trades,
                result.total_return,
            )
            start += self.step_bars

        return results

    def aggregate(self, results: List[BacktestResult]) -> dict[str, Any]:
        if not results:
            return {}
        return {
            "folds": len(results),
            "avg_return": sum(r.total_return for r in results) / len(results),
            "avg_sharpe": sum(r.sharpe_ratio for r in results) / len(results),
            "avg_max_dd": sum(r.max_drawdown for r in results) / len(results),
            "total_trades": sum(r.num_trades for r in results),
            "avg_win_rate": sum(r.win_rate for r in results) / len(results),
        }
