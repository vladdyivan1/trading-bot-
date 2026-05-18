"""Post-trade review helpers."""

from __future__ import annotations

from typing import Any

from ai.llm_client import LLMClient, LLMTradeReview


class TradeReviewer:
    """Ask the LLM to explain trade outcomes and weaknesses."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def review_trade(self, trade: dict[str, Any], context: dict[str, Any]) -> LLMTradeReview:
        prompt = (
            "Review this completed trade. Identify whether the loss/win was consistent with the strategy, "
            "what risk factors were present, and what should be backtested next."
        )
        return self.llm_client.review_trade({"trade": trade, "context": context}, prompt)
