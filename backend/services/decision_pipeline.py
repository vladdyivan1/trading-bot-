from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.llm_decision import DecisionContext, ExternalLLMDecisionEngine, LLMDecisionEngine, MockLLMDecisionEngine
from ai.news_providers import MockNewsProvider, NewsApiProvider, NewsProvider
from ai.sentiment_engine import SentimentEngine
from backend.models.entities import AlertEvent, ExecutionRecord, NewsSnapshot
from backend.schemas.decision import DecisionPayload, DecisionType, MarketRegime, NewsSentiment, OptionDirection
from backend.schemas.tradingview import TradingViewAlert
from backend.services.idempotency import idempotency_key
from backend.services.regime_classifier import RegimeClassifier
from backend.services.risk_engine import RiskEngine
from backend.services.settings import settings
from execution import ExecutionAdapter, ExecutionRequest, IBKRExecutionAdapter, PaperExecutionAdapter, TradierExecutionAdapter

logger = logging.getLogger(__name__)


class DecisionPipeline:
    def __init__(self) -> None:
        self.sentiment_engine = SentimentEngine()
        self.regime_classifier = RegimeClassifier()
        self.risk_engine = RiskEngine()
        self.llm_engine: LLMDecisionEngine = self._llm_engine()
        self.news_provider = self._news_provider()
        self.execution_adapter = self._execution_adapter()
        self.decision_adapter = TypeAdapter(DecisionPayload)


    def _llm_engine(self) -> LLMDecisionEngine:
        if settings.mock_ai_provider:
            return MockLLMDecisionEngine()
        return ExternalLLMDecisionEngine()

    def _news_provider(self) -> NewsProvider:
        if settings.news_filtering_enabled and not settings.mock_news_provider and settings.news_api_url and settings.news_api_key:
            return NewsApiProvider(base_url=settings.news_api_url, api_key=settings.news_api_key)
        return MockNewsProvider()

    def _execution_adapter(self) -> ExecutionAdapter:
        if settings.paper_trading_mode:
            return PaperExecutionAdapter()
        adapter = getattr(settings, "broker_adapter", "paper").lower()
        if adapter == "tradier":
            return TradierExecutionAdapter()
        if adapter == "ibkr":
            return IBKRExecutionAdapter()
        return PaperExecutionAdapter()

    def _technical_fallback_decision(self, alert: TradingViewAlert) -> DecisionPayload:
        bias = alert.bias.lower()
        direction = OptionDirection.NONE
        if bias == "bullish":
            direction = OptionDirection.CALL
        elif bias == "bearish":
            direction = OptionDirection.PUT
        decision = DecisionType.APPROVE if direction != OptionDirection.NONE else DecisionType.WAIT
        return DecisionPayload(
            decision=decision,
            direction=direction,
            confidence=50 if decision == DecisionType.APPROVE else 25,
            reason_summary="AI filtering disabled; using technical-only decision with reduced confidence.",
            news_sentiment=NewsSentiment.NEUTRAL,
            market_regime=MarketRegime.CHOP,
            risk_flags=[],
            size_modifier=0.75,
            metadata={"technical_only_mode": True},
        )

    def process_alert(self, db: Session, alert: TradingViewAlert) -> tuple[AlertEvent, DecisionPayload, bool]:
        key = idempotency_key(alert)
        existing = db.execute(select(AlertEvent).where(AlertEvent.idempotency_key == key)).scalar_one_or_none()
        if existing:
            decision = self.decision_adapter.validate_python(existing.decision_payload)
            return existing, decision, True

        duplicate_cutoff = datetime.now(UTC) - timedelta(seconds=settings.duplicate_window_seconds)
        near_dupe = db.execute(
            select(AlertEvent)
            .where(AlertEvent.symbol == alert.normalized_symbol())
            .where(AlertEvent.action == alert.action)
            .where(AlertEvent.received_at >= duplicate_cutoff)
            .order_by(AlertEvent.received_at.desc())
        ).scalar_one_or_none()

        headlines = []
        sentiment = NewsSentiment.NEUTRAL
        sentiment_score = 0.0
        sentiment_summary = "News filtering disabled."
        risk_flags: list[str] = []
        if settings.news_filtering_enabled:
            topics = ["SPY", "S&P 500", "Federal Reserve", "CPI", "jobs", "Treasury yields", "mega cap earnings"]
            headlines = self.news_provider.latest_headlines(topics=topics, limit=12)
            sent = self.sentiment_engine.evaluate(headlines)
            sentiment = sent.sentiment
            sentiment_score = sent.score
            sentiment_summary = sent.reason_summary
            risk_flags.extend(sent.risk_flags)

        regime = self.regime_classifier.classify(alert, risk_flags)
        if settings.ai_filtering_enabled:
            decision = self.llm_engine.decide(
                DecisionContext(
                    alert=alert,
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    market_regime=regime,
                    risk_flags=risk_flags,
                )
            )
        else:
            decision = self._technical_fallback_decision(alert)

        if near_dupe:
            decision.decision = DecisionType.REJECT
            decision.size_modifier = 0.0
            decision.risk_flags.append("DUPLICATE_WINDOW")
            decision.reason_summary += " Duplicate alert inside dedupe window."

        base_option_premium = max(0.75, (alert.atr or 2.0) * 0.35)
        proposed_qty = max(1, round(settings.default_contract_qty * max(decision.size_modifier, 0.1)))
        predicted_notional = base_option_premium * proposed_qty * 100
        risk = self.risk_engine.evaluate_pre_trade(
            db=db,
            alert=alert,
            predicted_notional=predicted_notional,
            event_risk_flags=risk_flags,
        )
        if not risk.allowed:
            decision.decision = risk.decision
            decision.size_modifier = min(decision.size_modifier, risk.size_modifier)
            decision.risk_flags.extend(risk.risk_flags or [])
            decision.risk_flags = sorted(set(decision.risk_flags))
            decision.reason_summary += f" {risk.reason}"
        elif risk.decision == DecisionType.REDUCE_SIZE:
            decision.decision = DecisionType.REDUCE_SIZE
            decision.size_modifier = min(decision.size_modifier, risk.size_modifier)
            decision.risk_flags.extend(risk.risk_flags or [])
            decision.reason_summary += f" {risk.reason}"

        execution_result: dict[str, Any] = {}
        pending_exec_row: ExecutionRecord | None = None
        if decision.decision in {DecisionType.APPROVE, DecisionType.REDUCE_SIZE} and decision.direction != OptionDirection.NONE:
            request = ExecutionRequest(
                underlying_symbol=alert.normalized_symbol(),
                direction=decision.direction,
                underlying_price=alert.price,
                quantity=max(1, round(settings.default_contract_qty * max(decision.size_modifier, 0.1))),
                max_spread_pct=settings.options_max_spread_pct,
                delta_min=settings.options_delta_min,
                delta_max=settings.options_delta_max,
                dte_preference=settings.options_default_dte,
                dte_fallback=settings.options_fallback_dte,
                min_open_interest=settings.options_min_open_interest,
                min_volume=settings.options_min_volume,
                max_hold_minutes=settings.max_hold_minutes_default,
                metadata={"source": "tradingview_webhook", "setup": alert.setup},
            )
            broker_result = self.execution_adapter.place_order(request)
            execution_result = {
                "accepted": broker_result.accepted,
                "status": broker_result.status,
                "reason": broker_result.reason,
                "contract_symbol": broker_result.contract_symbol,
            }
            if not broker_result.accepted:
                decision.decision = DecisionType.REJECT
                decision.size_modifier = 0.0
                decision.risk_flags.append("EXECUTION_REJECT")
                decision.reason_summary += f" Execution adapter rejected: {broker_result.reason}"
            else:
                self.risk_engine.register_open_trade(db, alert.event_time_utc(), broker_result.fill_price * broker_result.quantity * 100)
                exec_row = ExecutionRecord(
                    alert_event_id=0,  # placeholder updated after event insert
                    mode="paper" if settings.paper_trading_mode else "live",
                    status=broker_result.status,
                    symbol=alert.normalized_symbol(),
                    direction=decision.direction.value,
                    contract_symbol=broker_result.contract_symbol or "",
                    expiration=broker_result.expiration or "",
                    strike=broker_result.strike or 0.0,
                    delta=broker_result.delta or 0.0,
                    quantity=broker_result.quantity,
                    entry_price=broker_result.fill_price,
                    spread_pct=broker_result.spread_pct,
                    max_hold_minutes=settings.max_hold_minutes_default,
                    metadata=broker_result.metadata or {},
                )
                pending_exec_row = exec_row

        decision.reason_summary += f" {sentiment_summary}"
        decision.risk_flags = sorted(set(decision.risk_flags))
        payload = decision.model_dump(mode="json")
        payload["execution"] = execution_result

        event = AlertEvent(
            idempotency_key=key,
            payload_id=alert.payload_id,
            symbol=alert.normalized_symbol(),
            interval=alert.interval,
            action=alert.action,
            bias=alert.bias,
            setup=alert.setup,
            alert_time=alert.event_time_utc(),
            stale="STALE_ALERT" in decision.risk_flags,
            duplicate_of_event_id=near_dupe.id if near_dupe else None,
            raw_payload=alert.model_dump(mode="json"),
            decision_payload=payload,
        )
        db.add(event)
        db.flush()

        if pending_exec_row is not None:
            pending_exec_row.alert_event_id = event.id
            db.add(pending_exec_row)

        if settings.news_filtering_enabled:
            db.add(
                NewsSnapshot(
                    alert_event_id=event.id,
                    sentiment=sentiment.value,
                    regime_hint=regime.value,
                    reason_summary=sentiment_summary,
                    headlines=[item.to_dict() for item in headlines],
                )
            )

        db.commit()
        db.refresh(event)
        logger.info("Processed alert %s with decision %s", event.id, decision.decision.value)
        return event, decision, False
