"""LLM signal analysis — recommendations only, no order placement."""

from __future__ import annotations

import json

from ai.llm_client import LLMClient
from ai.prompts import TRADE_SETUP_PROMPT
from config.settings import get_settings
from database.db import get_session
from database.repositories import LLMRepository
from schemas import LLMRecommendation, TradeSignal


class SignalAnalyzer:
    """Scores trade setups via LLM structured output."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient(get_settings())

    def analyze(
        self,
        signal: TradeSignal,
        market_summary: dict | None = None,
        backtest_metrics: dict | None = None,
    ) -> LLMRecommendation:
        prompt = TRADE_SETUP_PROMPT.format(
            signal=json.dumps(signal.model_dump_json_safe(), indent=2),
            market=json.dumps(market_summary or {}, indent=2),
            backtest=json.dumps(backtest_metrics or {}, indent=2),
        )
        raw = self.llm.complete_json(
            system="You are a trading research assistant. Never execute trades.",
            user=prompt,
        )
        rec = LLMRecommendation.model_validate(raw)
        with get_session() as session:
            LLMRepository(session).log_response(signal.symbol, raw)
        return rec
