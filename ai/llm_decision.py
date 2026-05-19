"""LLM and rule-based decision engine to filter and score trade opportunities in real time."""
import json
import logging
from abc import ABC, abstractmethod

from backend.config import Settings, get_settings
from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import (
    AIDecision,
    DecisionAction,
    Direction,
    MarketRegime,
    NewsSentiment,
)
from ai.sentiment_engine import aggregate_sentiment, detect_event_risk, macro_contradiction

logger = logging.getLogger(__name__)


class DecisionEngine(ABC):
    @abstractmethod
    async def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        regime: MarketRegime,
        event_risk: bool,
    ) -> AIDecision:
        pass


class RuleBasedDecisionEngine(DecisionEngine):
    """Probabilistic filter without external LLM — used when API key absent."""

    async def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        regime: MarketRegime,
        event_risk: bool,
    ) -> AIDecision:
        sentiment_str, score = aggregate_sentiment(headlines)
        news_sentiment = NewsSentiment(sentiment_str)
        flags: list[str] = []

        if event_risk or detect_event_risk(headlines):
            flags.append("event_risk")
            return AIDecision(
                decision=DecisionAction.WAIT,
                direction=Direction.NONE,
                confidence=0.3,
                reason_summary="Elevated macro event risk; waiting for clarity.",
                news_sentiment=news_sentiment,
                market_regime=MarketRegime.EVENT_RISK,
                risk_flags=flags,
                headlines_used=len(headlines),
            )

        direction = Direction.NONE
        if alert.is_bullish:
            direction = Direction.CALL
        elif alert.is_bearish:
            direction = Direction.PUT

        if direction == Direction.NONE:
            return AIDecision(
                decision=DecisionAction.WAIT,
                direction=Direction.NONE,
                confidence=0.25,
                reason_summary="No clear technical bias from alert.",
                news_sentiment=news_sentiment,
                market_regime=regime,
                headlines_used=len(headlines),
            )

        confidence = 0.55
        if (direction == Direction.CALL and news_sentiment == NewsSentiment.BULLISH) or (
            direction == Direction.PUT and news_sentiment == NewsSentiment.BEARISH
        ):
            confidence = 0.72
        elif macro_contradiction(alert.is_bullish, alert.is_bearish, sentiment_str):
            flags.append("news_technical_contradiction")
            return AIDecision(
                decision=DecisionAction.REDUCE_SIZE,
                direction=direction,
                confidence=0.4,
                reason_summary="Strong technicals but macro headlines contradict; reduced size.",
                news_sentiment=news_sentiment,
                market_regime=regime,
                risk_flags=flags,
                size_modifier=0.5,
                headlines_used=len(headlines),
            )

        if regime == MarketRegime.CHOP:
            confidence *= 0.85
            flags.append("chop_regime")
        if regime == MarketRegime.HIGH_VOL:
            flags.append("high_volatility")
            confidence *= 0.9

        if not headlines:
            confidence = 0.42
            flags.append("no_news_fallback")

        action = DecisionAction.APPROVE if confidence >= 0.5 else DecisionAction.WAIT
        return AIDecision(
            decision=action,
            direction=direction,
            confidence=round(confidence, 2),
            reason_summary=(
                f"Probabilistic filter: {direction.value} setup aligns with "
                f"{news_sentiment.value} news flow (not certainty)."
            ),
            news_sentiment=news_sentiment,
            market_regime=regime,
            risk_flags=flags,
            size_modifier=1.0 if action == DecisionAction.APPROVE else 0.5,
            headlines_used=len(headlines),
            technical_only=not headlines,
        )


class LLMDecisionEngine(DecisionEngine):
    """OpenAI-backed structured decision when API key is configured."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.fallback = RuleBasedDecisionEngine()

    async def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        regime: MarketRegime,
        event_risk: bool,
    ) -> AIDecision:
        if not self.api_key:
            return await self.fallback.evaluate(alert, headlines, regime, event_risk)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            prompt = self._build_prompt(alert, headlines, regime, event_risk)
            resp = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You filter and score SPY 0DTE options scalp opportunities. "
                            "Never claim certainty. Return JSON only with keys: decision, direction, "
                            "confidence, reason_summary, news_sentiment, market_regime, risk_flags, size_modifier."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            return AIDecision(
                decision=DecisionAction(data.get("decision", "WAIT")),
                direction=Direction(data.get("direction", "NONE")),
                confidence=float(data.get("confidence", 0.5)),
                reason_summary=data.get("reason_summary", ""),
                news_sentiment=NewsSentiment(data.get("news_sentiment", "NEUTRAL")),
                market_regime=MarketRegime(data.get("market_regime", regime.value)),
                risk_flags=data.get("risk_flags", []),
                size_modifier=float(data.get("size_modifier", 1.0)),
                headlines_used=len(headlines),
            )
        except Exception as e:
            logger.warning("LLM decision failed, using rule fallback: %s", e)
            return await self.fallback.evaluate(alert, headlines, regime, event_risk)

    def _build_prompt(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        regime: MarketRegime,
        event_risk: bool,
    ) -> str:
        return json.dumps(
            {
                "task": "filter_and_score_trade_opportunity",
                "alert": alert.model_dump(exclude={"raw_payload"}),
                "headlines": headlines[:10],
                "regime": regime.value,
                "event_risk": event_risk,
                "rules": [
                    "Approve calls when bullish technicals + supportive news",
                    "Approve puts when bearish technicals + supportive news",
                    "REJECT or WAIT on imminent high-impact events",
                    "REDUCE_SIZE on technical/news contradiction",
                ],
            },
            default=str,
        )


class MockAIDecisionEngine(DecisionEngine):
    """Fixed responses for integration tests."""

    def __init__(self, decision: DecisionAction = DecisionAction.APPROVE):
        self._decision = decision

    async def evaluate(
        self,
        alert: TradingViewAlert,
        headlines: list[dict],
        regime: MarketRegime,
        event_risk: bool,
    ) -> AIDecision:
        direction = Direction.CALL if alert.is_bullish else Direction.PUT if alert.is_bearish else Direction.NONE
        return AIDecision(
            decision=self._decision,
            direction=direction,
            confidence=0.7,
            reason_summary="Mock AI approval for testing",
            news_sentiment=NewsSentiment.NEUTRAL,
            market_regime=regime,
            headlines_used=len(headlines),
        )


def get_decision_engine(settings: Settings | None = None) -> DecisionEngine:
    settings = settings or get_settings()
    if settings.openai_api_key:
        return LLMDecisionEngine(settings.openai_api_key, settings.openai_model)
    return RuleBasedDecisionEngine()
