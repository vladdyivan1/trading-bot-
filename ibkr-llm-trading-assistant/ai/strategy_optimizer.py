"""Strategy performance review and parameter suggestions."""

from __future__ import annotations

from typing import Any, Optional

from ai.llm_client import LLMClient
from ai.prompts import STRATEGY_OPTIMIZER_PROMPT, SYSTEM_PROMPT
from database.db import get_db_session
from database.repositories import StrategyPerformanceRepository


class StrategyOptimizer:
    """
    Self-improvement loop: ranks strategies, suggests parameters.
    Requires human approval before live promotion.
    """

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def update_rankings(
        self,
        strategy_name: str,
        symbol: str,
        asset_class: str,
        timeframe: str,
        total_trades: int,
        wins: int,
        total_pnl: float,
        expectancy: float,
        sharpe: float,
    ) -> float:
        win_rate = wins / total_trades if total_trades > 0 else 0
        rank_score = (
            expectancy * 0.4
            + sharpe * 0.3
            + win_rate * 0.2
            + min(total_trades / 100, 1.0) * 0.1
        )
        with get_db_session() as session:
            StrategyPerformanceRepository(session).upsert_performance(
                strategy_name=strategy_name,
                symbol=symbol,
                asset_class=asset_class,
                timeframe=timeframe,
                total_trades=total_trades,
                wins=wins,
                total_pnl=total_pnl,
                expectancy=expectancy,
                sharpe_ratio=sharpe,
                rank_score=rank_score,
            )
        return rank_score

    def suggest_improvements(
        self,
        strategy_name: str,
        performance: dict[str, Any],
        walk_forward: dict[str, Any],
    ) -> dict:
        if not self.llm.is_available():
            return {"requires_human_approval": True, "error": "LLM not configured"}
        prompt = STRATEGY_OPTIMIZER_PROMPT.format(
            strategy_name=strategy_name,
            performance=performance,
            walk_forward=walk_forward,
        )
        result = self.llm.complete_json(SYSTEM_PROMPT, prompt)
        result["requires_human_approval"] = True
        result["promotion_ready"] = result.get("promotion_ready", False)
        return result

    def get_top_strategies(self, limit: int = 10) -> list:
        with get_db_session() as session:
            return StrategyPerformanceRepository(session).get_ranked_strategies(limit)
