"""Signal review workflow combining market, backtest, and LLM."""

from __future__ import annotations

from ai.llm_client import LLMClient, LLMTradeReview
from ai.prompts import SIGNAL_ANALYSIS_PROMPT
from database.repositories import LLMRecommendationRepository
from strategies.base_strategy import StrategySignal


class SignalAnalyzer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()
        self.repo = LLMRecommendationRepository()

    def review_signal(
        self,
        signal: StrategySignal,
        market_summary: dict,
        backtest_metrics: dict,
    ) -> LLMTradeReview:
        payload = {
            "signal": signal.model_dump(mode="json"),
            "market_summary": market_summary,
            "backtest": backtest_metrics,
        }
        result = self.llm_client.analyze(payload=payload, user_prompt=SIGNAL_ANALYSIS_PROMPT)
        self.repo.log("signal_review", payload=payload, response=result.model_dump(mode="json"))
        return result
