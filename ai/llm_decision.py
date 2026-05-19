"""Mockable AI decision engine for combining technical and news context."""

from __future__ import annotations

from ai.sentiment_engine import NewsAnalysis
from backend.schemas.decision import DecisionResponse
from backend.schemas.tradingview import TradingViewAlert


class LlmDecisionEngine:
    """Deterministic stand-in for an LLM-assisted decision layer.

    The output intentionally filters and scores trade opportunities in real time
    instead of claiming certainty about future price direction.
    """

    def decide(
        self,
        alert: TradingViewAlert,
        news: NewsAnalysis,
        market_regime: str,
        feature_flags: dict[str, bool],
    ) -> DecisionResponse:
        direction = alert.direction
        risk_flags = list(news.risk_flags)
        confidence = 0.58
        size_modifier = 1.0
        decision = "APPROVE"

        if direction == "NONE":
            return DecisionResponse(
                decision="REJECT",
                direction="NONE",
                confidence=0.0,
                reason_summary="Alert did not include a bullish or bearish options bias.",
                news_sentiment=news.sentiment,
                market_regime=market_regime,
                risk_flags=risk_flags,
                rejection_reasons=["NO_DIRECTION"],
                size_modifier=0.0,
            )

        supportive = (
            (direction == "CALL" and news.sentiment in {"BULLISH", "NEUTRAL"})
            or (direction == "PUT" and news.sentiment in {"BEARISH", "NEUTRAL"})
        )
        contradictory = (
            (direction == "CALL" and news.sentiment == "BEARISH")
            or (direction == "PUT" and news.sentiment == "BULLISH")
        )

        if not feature_flags.get("news_filter", True):
            supportive = True
            contradictory = False
            risk_flags.append("NEWS_FILTER_DISABLED")

        if market_regime == "TREND":
            confidence += 0.12
        elif market_regime == "HIGH_VOL":
            confidence -= 0.10
            size_modifier = min(size_modifier, 0.5)
            risk_flags.append("HIGH_VOL_REGIME")
        elif market_regime == "CHOP":
            confidence -= 0.08
            size_modifier = min(size_modifier, 0.7)
            risk_flags.append("CHOPPY_REGIME")
        elif market_regime == "EVENT_RISK":
            confidence -= 0.25
            decision = "WAIT"
            size_modifier = 0.0

        if "EVENT_RISK_HEADLINES" in risk_flags:
            decision = "WAIT"
            confidence -= 0.18
            size_modifier = 0.0
        elif contradictory:
            decision = "REDUCE_SIZE"
            confidence -= 0.12
            size_modifier = min(size_modifier, 0.5)
            risk_flags.append("TECHNICAL_NEWS_CONTRADICTION")
        elif not supportive:
            decision = "WAIT"
            confidence -= 0.10
            size_modifier = 0.0

        if "NO_NEWS_AVAILABLE" in risk_flags:
            confidence -= 0.10
            size_modifier = min(size_modifier, 0.75)

        confidence = max(0.0, min(confidence, 0.95))
        reason = (
            f"{alert.bias.title()} technical setup maps to {direction}; "
            f"headline sentiment is {news.sentiment.lower()}, regime is {market_regime.lower()}. "
            f"{news.summary}"
        )
        return DecisionResponse(
            decision=decision,
            direction=direction,
            confidence=confidence,
            reason_summary=reason,
            news_sentiment=news.sentiment,
            market_regime=market_regime,
            risk_flags=risk_flags,
            rejection_reasons=[],
            size_modifier=size_modifier,
        )
