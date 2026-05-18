"""Strategy ranking and conservative parameter suggestion module."""

from __future__ import annotations

from ai.llm_client import LLMClient
from ai.prompts import STRATEGY_OPTIMIZER_PROMPT


class StrategyOptimizer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def suggest(self, performance_snapshot: dict, constraints: dict | None = None) -> dict:
        payload = {
            "performance": performance_snapshot,
            "constraints": constraints or {
                "must_run_walk_forward": True,
                "human_approval_required": True,
            },
        }
        result = self.llm_client.analyze(payload=payload, user_prompt=STRATEGY_OPTIMIZER_PROMPT)
        return {
            "strategy_rankings": performance_snapshot.get("rankings", []),
            "llm_review": result.model_dump(mode="json"),
            "requires_human_approval": True,
        }
