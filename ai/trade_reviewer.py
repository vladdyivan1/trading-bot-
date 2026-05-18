"""Post-trade review and diagnosis workflow."""

from __future__ import annotations

from ai.llm_client import LLMClient, LLMTradeReview
from database.repositories import LLMRecommendationRepository


class TradeReviewer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.repo = LLMRecommendationRepository()

    def review_trade(self, trade: dict, context: dict) -> LLMTradeReview:
        payload = {"trade": trade, "context": context}
        prompt = (
            "Review this completed trade, identify weaknesses, and suggest what to backtest next. "
            "Return JSON only matching the agreed schema."
        )
        result = self.llm_client.analyze(payload=payload, user_prompt=prompt)
        self.repo.log("trade_review", payload=payload, response=result.model_dump(mode="json"))
        return result
