"""Strategy performance feedback and ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai.llm_client import LLMClient
from ai.prompts import STRATEGY_OPTIMIZER_PROMPT


@dataclass
class StrategyScore:
    strategy: str
    symbol: str
    timeframe: str
    score: float
    metrics: dict[str, Any] = field(default_factory=dict)


class StrategyOptimizer:
    """Rank strategies and request parameter ideas for walk-forward testing."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def rank(self, performance_rows: list[dict[str, Any]]) -> list[StrategyScore]:
        scores: list[StrategyScore] = []
        for row in performance_rows:
            metrics = row.get("metrics", {})
            score = (
                float(metrics.get("expectancy", 0.0))
                + float(metrics.get("sharpe_ratio", 0.0)) * 10
                + float(metrics.get("total_return", 0.0)) * 100
                + float(metrics.get("max_drawdown", 0.0)) * 100
            )
            scores.append(
                StrategyScore(
                    strategy=row["strategy"],
                    symbol=row["symbol"],
                    timeframe=row["timeframe"],
                    score=score,
                    metrics=metrics,
                )
            )
        return sorted(scores, key=lambda item: item.score, reverse=True)

    def suggest_parameters(self, performance_summary: dict[str, Any]) -> dict[str, Any]:
        review = self.llm_client.review_trade(performance_summary, STRATEGY_OPTIMIZER_PROMPT)
        return {
            "requires_walk_forward_validation": True,
            "requires_human_approval": True,
            "llm_review": review.dict(),
        }
