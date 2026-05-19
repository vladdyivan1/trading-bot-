from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.schemas.decision import DecisionPayload, DecisionType, MarketRegime, NewsSentiment, OptionDirection
from backend.schemas.tradingview import TradingViewAlert


@dataclass(slots=True)
class DecisionContext:
    alert: TradingViewAlert
    sentiment: NewsSentiment
    sentiment_score: float
    market_regime: MarketRegime
    risk_flags: list[str]


class LLMDecisionEngine:
    """Heuristic decision engine with optional LLM extension point."""

    def decide(self, context: DecisionContext) -> DecisionPayload:
        bias = context.alert.bias.lower()
        bullish_signal = bias == "bullish" and context.alert.action.lower() in {"buy", "long", "entry", "buy_call"}
        bearish_signal = bias == "bearish" and context.alert.action.lower() in {"sell", "short", "entry", "buy_put"}

        direction = OptionDirection.NONE
        if bullish_signal:
            direction = OptionDirection.CALL
        elif bearish_signal:
            direction = OptionDirection.PUT

        confidence = 45
        decision = DecisionType.WAIT
        reasons = ["Technical signal received; evaluating news and regime alignment."]
        size_modifier = 0.5

        aligned_bull = bullish_signal and context.sentiment in {NewsSentiment.BULLISH, NewsSentiment.NEUTRAL}
        aligned_bear = bearish_signal and context.sentiment in {NewsSentiment.BEARISH, NewsSentiment.NEUTRAL}
        contradictory = (bullish_signal and context.sentiment == NewsSentiment.BEARISH) or (
            bearish_signal and context.sentiment == NewsSentiment.BULLISH
        )

        if context.market_regime == MarketRegime.EVENT_RISK or any(flag.startswith("EVENT:") for flag in context.risk_flags):
            decision = DecisionType.WAIT
            confidence = 20
            size_modifier = 0.0
            reasons.append("Event-risk regime active; delaying entries.")
        elif aligned_bull or aligned_bear:
            decision = DecisionType.APPROVE
            confidence = 72
            size_modifier = 1.0
            reasons.append("Technical and sentiment context are directionally aligned.")
        elif contradictory:
            decision = DecisionType.REDUCE_SIZE
            confidence = 40
            size_modifier = 0.35
            reasons.append("Technical setup conflicts with headline flow; reducing risk.")
        else:
            reasons.append("Signal quality insufficient for full-size entry.")

        if context.market_regime == MarketRegime.HIGH_VOL and decision == DecisionType.APPROVE:
            decision = DecisionType.REDUCE_SIZE
            confidence = max(confidence - 15, 30)
            size_modifier = min(size_modifier, 0.5)
            reasons.append("High-volatility regime detected, reducing size.")

        if direction == OptionDirection.NONE:
            decision = DecisionType.REJECT
            confidence = 10
            size_modifier = 0.0
            reasons.append("Direction could not be mapped to CALL/PUT options flow.")

        return DecisionPayload(
            decision=decision,
            direction=direction,
            confidence=confidence,
            reason_summary=" ".join(reasons),
            news_sentiment=context.sentiment,
            market_regime=context.market_regime,
            risk_flags=context.risk_flags,
            size_modifier=size_modifier,
            metadata={
                "sentiment_score": context.sentiment_score,
                "probabilistic": True,
            },
        )


class MockLLMDecisionEngine(LLMDecisionEngine):
    """Explicit mock engine used for tests/offline development."""


class ExternalLLMDecisionEngine(LLMDecisionEngine):
    """Placeholder for future provider-backed LLM decisions."""

    def decide(self, context: DecisionContext) -> DecisionPayload:
        return super().decide(context)
