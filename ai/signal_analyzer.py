"""LLM-assisted signal analysis."""

from __future__ import annotations

from typing import Any

from ai.llm_client import LLMClient, LLMTradeReview
from ai.prompts import TRADE_REVIEW_PROMPT
from strategies.base_strategy import TradeSignal


class SignalAnalyzer:
    """Convert deterministic signals and evidence into LLM reviews."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def analyze(
        self,
        signal: TradeSignal,
        backtest_metrics: dict[str, Any],
        market_summary: dict[str, Any],
        strategy_performance: dict[str, Any] | None = None,
    ) -> LLMTradeReview:
        payload = {
            "signal": signal.dict(),
            "backtest_metrics": backtest_metrics,
            "market_summary": market_summary,
            "strategy_performance": strategy_performance or {},
            "safety_rule": "LLM output is advisory only and cannot place trades.",
        }
        return self.llm_client.review_trade(payload, TRADE_REVIEW_PROMPT)
