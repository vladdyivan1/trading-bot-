"""LLM review of completed trades."""

from __future__ import annotations

import json

from ai.llm_client import LLMClient
from ai.prompts import TRADE_REVIEW_PROMPT


class TradeReviewer:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def review_losing_trade(self, trade: dict) -> dict:
        prompt = TRADE_REVIEW_PROMPT.format(trade=json.dumps(trade, indent=2, default=str))
        return self.llm.complete_json(
            system="You review losing trades for process improvement.",
            user=prompt,
        )
