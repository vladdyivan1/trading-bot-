"""Review winning and losing trades with LLM."""

from __future__ import annotations

from typing import Any, Optional

from ai.llm_client import LLMClient
from ai.prompts import LOSING_TRADE_REVIEW_PROMPT, SYSTEM_PROMPT


class TradeReviewer:
    """Post-trade analysis for learning loop."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def review_losing_trade(self, trade: dict, context: dict) -> dict:
        if not self.llm.is_available():
            return {"error": "LLM not configured"}
        prompt = LOSING_TRADE_REVIEW_PROMPT.format(trade=trade, context=context)
        return self.llm.complete_json(SYSTEM_PROMPT, prompt)

    def review_batch(self, trades: list[dict]) -> list[dict]:
        losers = [t for t in trades if t.get("pnl", 0) < 0]
        return [self.review_losing_trade(t, {}) for t in losers[:10]]
