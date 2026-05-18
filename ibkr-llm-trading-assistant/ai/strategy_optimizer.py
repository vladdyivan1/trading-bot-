"""Self-improvement: strategy ranking and parameter suggestions."""

from __future__ import annotations

import json

from ai.llm_client import LLMClient
from ai.prompts import STRATEGY_OPTIMIZER_PROMPT
from backtesting.walk_forward import WalkForwardValidator
from database.db import get_session
from database.repositories import StrategyPerformanceRepository
from strategies.base_strategy import BaseStrategy


class StrategyOptimizer:
    """
    Performance feedback loop.

    Adjusts rankings from paper/backtest results. Parameter promotion requires
    walk-forward validation and human approval before live trading.
    """

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.walk_forward = WalkForwardValidator()

    def get_rankings(self, limit: int = 20) -> list[dict]:
        with get_session() as session:
            rows = StrategyPerformanceRepository(session).get_rankings(limit)
        return [
            {
                "strategy": r.strategy_name,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "ranking_score": r.ranking_score,
                "win_rate": r.win_rate,
                "expectancy": r.expectancy,
            }
            for r in rows
        ]

    def suggest_next_tests(self, performance: list[dict]) -> dict:
        prompt = STRATEGY_OPTIMIZER_PROMPT.format(
            performance=json.dumps(performance, indent=2)
        )
        return self.llm.complete_json(
            system="Suggest backtests only. Never approve live deployment.",
            user=prompt,
        )

    def validate_new_params(
        self,
        strategy: BaseStrategy,
        df,
        symbol: str,
        min_folds: int = 2,
    ) -> dict:
        """Walk-forward validation before parameter promotion."""
        results = self.walk_forward.run(strategy, df, symbol)
        agg = self.walk_forward.aggregate(results)
        agg["approved_for_paper"] = agg.get("folds", 0) >= min_folds and agg.get("avg_sharpe", 0) > 0
        agg["approved_for_live"] = False  # Always requires human
        return agg
