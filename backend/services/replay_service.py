from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.llm_decision import DecisionContext, LLMDecisionEngine
from ai.news_providers import MockNewsProvider
from ai.sentiment_engine import SentimentEngine
from backend.models.entities import AlertEvent
from backend.schemas.decision import DecisionType, NewsSentiment, OptionDirection
from backend.schemas.tradingview import TradingViewAlert
from backend.services.regime_classifier import RegimeClassifier
from backend.services.risk_engine import RiskEngine


class ReplayService:
    def __init__(self) -> None:
        self.sentiment_engine = SentimentEngine()
        self.news_provider = MockNewsProvider()
        self.llm_engine = LLMDecisionEngine()
        self.regime_classifier = RegimeClassifier()
        self.risk_engine = RiskEngine()

    def _baseline_technical(self, alert: TradingViewAlert) -> DecisionType:
        if alert.bias.lower() in {"bullish", "bearish"}:
            return DecisionType.APPROVE
        return DecisionType.WAIT

    def run(self, db: Session, limit: int = 1_000) -> dict[str, Any]:
        events = db.execute(select(AlertEvent).order_by(AlertEvent.received_at.asc()).limit(limit)).scalars().all()
        base_counts: Counter[str] = Counter()
        ai_counts: Counter[str] = Counter()
        ai_risk_counts: Counter[str] = Counter()

        rows: list[dict[str, Any]] = []
        for event in events:
            alert = TradingViewAlert.model_validate(event.raw_payload)
            base_decision = self._baseline_technical(alert)
            base_counts[base_decision.value] += 1

            sentiment_result = self.sentiment_engine.evaluate(
                self.news_provider.latest_headlines(["SPY", "macro"], limit=10)
            )
            regime = self.regime_classifier.classify(alert, sentiment_result.risk_flags)
            ai_decision = self.llm_engine.decide(
                DecisionContext(
                    alert=alert,
                    sentiment=sentiment_result.sentiment,
                    sentiment_score=sentiment_result.score,
                    market_regime=regime,
                    risk_flags=sentiment_result.risk_flags,
                )
            )
            ai_counts[ai_decision.decision.value] += 1

            rough_notional = max(75.0, (alert.atr or 2.0) * 35.0)
            risk_outcome = self.risk_engine.evaluate_pre_trade(
                db=db,
                alert=alert,
                predicted_notional=rough_notional,
                event_risk_flags=sentiment_result.risk_flags,
            )
            final_decision = ai_decision.decision if risk_outcome.allowed else risk_outcome.decision
            ai_risk_counts[final_decision.value] += 1

            rows.append(
                {
                    "event_id": event.id,
                    "time": alert.event_time_utc().isoformat(),
                    "symbol": alert.normalized_symbol(),
                    "baseline": base_decision.value,
                    "ai_filter": ai_decision.decision.value,
                    "ai_risk": final_decision.value,
                }
            )

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "events_evaluated": len(events),
            "base_strategy_counts": dict(base_counts),
            "pine_plus_ai_counts": dict(ai_counts),
            "pine_plus_ai_plus_risk_counts": dict(ai_risk_counts),
            "rows": rows,
        }
