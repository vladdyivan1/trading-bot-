"""LLM signal analysis — advisory only."""

from __future__ import annotations

from typing import Any, Optional

from ai.llm_client import LLMClient
from ai.prompts import SYSTEM_PROMPT, TRADE_REVIEW_PROMPT
from database.db import get_db_session
from database.repositories import LLMRepository
from schemas import BacktestResult, LLMTradeReview, TradeSignal


class SignalAnalyzer:
    """Score and explain trade setups via LLM."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def analyze(
        self,
        signal: TradeSignal,
        market_summary: dict[str, Any],
        backtest_result: Optional[BacktestResult] = None,
        performance: Optional[dict] = None,
    ) -> LLMTradeReview:
        if not self.llm.is_available():
            return LLMTradeReview(
                trade_allowed=False,
                setup_quality=0.0,
                reasoning="LLM API key not configured",
                risks=["LLM unavailable"],
            )

        bt_metrics = backtest_result.model_dump() if backtest_result else {}
        prompt = TRADE_REVIEW_PROMPT.format(
            signal=signal.model_dump_json(),
            market_summary=market_summary,
            backtest_metrics=bt_metrics,
            performance=performance or {},
        )
        data = self.llm.complete_json(SYSTEM_PROMPT, prompt)
        review = LLMTradeReview(**{k: v for k, v in data.items() if k in LLMTradeReview.model_fields})

        with get_db_session() as session:
            LLMRepository(session).save_recommendation(
                "signal_analysis",
                f"{signal.symbol} {signal.strategy_name}",
                review.model_dump(),
            )
        return review
