"""AI/LLM decision engine with mock provider for testing."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from backend.config import Settings
from backend.schemas.alerts import (
    AIDecisionResponse,
    Decision,
    Direction,
    MarketRegime,
    Sentiment,
    TradingViewAlert,
)
from ai.sentiment_engine import aggregate_sentiment, detect_event_risk, score_headline

logger = logging.getLogger(__name__)


class DecisionEngine(ABC):
    @abstractmethod
    def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        news_sentiment: str,
        event_risk: bool,
        regime: MarketRegime,
    ) -> AIDecisionResponse:
        pass


class MockDecisionEngine(DecisionEngine):
    """Probabilistic filter — does not claim predictive certainty."""

    def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        news_sentiment: str,
        event_risk: bool,
        regime: MarketRegime,
    ) -> AIDecisionResponse:
        bias = (alert.bias or alert.action or "").lower()
        is_bull = "bull" in bias or alert.action == "buy"
        is_bear = "bear" in bias or alert.action == "sell"

        scores = [score_headline(h.get("title", "")) for h in headlines]
        agg = aggregate_sentiment(scores) if scores else news_sentiment
        event_flags = detect_event_risk([h.get("title", "") for h in headlines])

        if event_risk or event_flags:
            return AIDecisionResponse(
                decision=Decision.WAIT,
                direction=Direction.NONE,
                confidence=0.3,
                reason_summary="Elevated event risk — waiting for clarity before 0DTE entry.",
                news_sentiment=Sentiment.MIXED,
                market_regime=MarketRegime.EVENT_RISK,
                risk_flags=event_flags or ["EVENT_RISK"],
                size_modifier=0.0,
            )

        direction = Direction.NONE
        if is_bull and not is_bear:
            direction = Direction.CALL
        elif is_bear and not is_bull:
            direction = Direction.PUT

        if direction == Direction.NONE:
            return AIDecisionResponse(
                decision=Decision.WAIT,
                direction=Direction.NONE,
                confidence=0.4,
                reason_summary="No clear directional bias from technical setup.",
                news_sentiment=Sentiment(agg) if agg in Sentiment.__members__ else Sentiment.NEUTRAL,
                market_regime=regime,
                risk_flags=[],
                size_modifier=0.0,
            )

        tech_bull = direction == Direction.CALL
        news_bull = agg in ("BULLISH",)
        news_bear = agg in ("BEARISH",)
        contradictory = (tech_bull and news_bear) or (not tech_bull and news_bull)

        confidence = 0.65
        if not headlines:
            confidence = 0.45
            reason = "Technical-only filter (no news); lower confidence scoring."
        elif contradictory:
            return AIDecisionResponse(
                decision=Decision.REDUCE_SIZE,
                direction=direction,
                confidence=0.4,
                reason_summary="Technical breakout conflicts with headline flow — reduced size.",
                news_sentiment=Sentiment.MIXED,
                market_regime=regime,
                risk_flags=["TECH_NEWS_CONFLICT"],
                size_modifier=0.5,
            )
        else:
            reason = "Technicals and news flow align for probabilistic approval."
            confidence = 0.75

        if regime == MarketRegime.CHOP:
            confidence *= 0.85
            reason += " Choppy regime lowers conviction."

        if regime == MarketRegime.HIGH_VOL:
            confidence *= 0.9

        return AIDecisionResponse(
            decision=Decision.APPROVE,
            direction=direction,
            confidence=min(confidence, 0.95),
            reason_summary=reason,
            news_sentiment=Sentiment(agg) if agg in Sentiment.__members__ else Sentiment.NEUTRAL,
            market_regime=regime,
            risk_flags=[],
            size_modifier=1.0,
        )


class OpenAIDecisionEngine(DecisionEngine):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        news_sentiment: str,
        event_risk: bool,
        regime: MarketRegime,
    ) -> AIDecisionResponse:
        try:
            import httpx

            prompt = {
                "task": "Filter and score trade opportunities in real time. Do not claim certainty.",
                "alert": alert.model_dump(),
                "headlines": headlines[:10],
                "news_sentiment": news_sentiment,
                "event_risk": event_risk,
                "regime": regime.value,
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You filter 0DTE SPY options scalps. Return JSON only with keys: "
                                    "decision, direction, confidence, reason_summary, news_sentiment, "
                                    "market_regime, risk_flags, size_modifier"
                                ),
                            },
                            {"role": "user", "content": json.dumps(prompt)},
                        ],
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    data = json.loads(content.strip().strip("`").replace("json\n", ""))
                    return AIDecisionResponse.model_validate(data)
        except Exception as e:
            logger.warning("OpenAI decision failed: %s", e)
        return MockDecisionEngine().evaluate(alert, headlines, news_sentiment, event_risk, regime)


def get_decision_engine(settings: Settings) -> DecisionEngine:
    if settings.ai_provider == "openai" and settings.openai_api_key:
        return OpenAIDecisionEngine(settings.openai_api_key, settings.openai_model)
    return MockDecisionEngine()
