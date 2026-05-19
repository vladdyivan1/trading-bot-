"""Orchestrate webhook: normalize → AI → risk → execution."""

import logging
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.models.entities import AIDecisionRecord, AlertRecord, NewsSnapshot, TradeExecution
from backend.schemas.alerts import AIDecisionResponse, Decision, Direction, TradingViewAlert, WebhookResponse
from backend.services.alert_normalizer import generate_alert_id, normalize_alert
from backend.services.options_selector import OptionsSelector
from backend.services.regime_classifier import classify_regime
from backend.services.risk_engine import RiskEngine
from ai.llm_decision import get_decision_engine
from ai.news_providers import get_news_provider
from execution.paper_executor import get_executor

logger = logging.getLogger(__name__)


class WebhookProcessor:
    def __init__(self, db: Session, settings: Optional[Settings] = None):
        self.db = db
        self.settings = settings or get_settings()
        self.risk = RiskEngine(self.settings)
        self.options = OptionsSelector(self.settings)
        self.news = get_news_provider(self.settings)
        self.ai = get_decision_engine(self.settings)
        self.executor = get_executor(self.settings)

    def process(self, raw: dict[str, Any]) -> WebhookResponse:
        start = time.perf_counter()
        alert_id = generate_alert_id(raw)

        existing = self.db.query(AlertRecord).filter(AlertRecord.alert_id == alert_id).first()
        if existing and existing.processed:
            return WebhookResponse(
                status="duplicate",
                alert_id=alert_id,
                rejection_reason="IDEMPOTENT_DUPLICATE",
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        if not existing:
            record = AlertRecord(alert_id=alert_id, payload=raw)
            self.db.add(record)
            self.db.commit()

        if raw.get("secret") and raw.get("secret") != self.settings.webhook_secret:
            return WebhookResponse(
                status="rejected",
                alert_id=alert_id,
                rejection_reason="INVALID_WEBHOOK_SECRET",
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        alert = normalize_alert(raw)
        regime = classify_regime(alert)

        headlines = []
        news_sentiment = "NEUTRAL"
        event_risk = False
        if self.settings.enable_news_filter:
            snap = self.news.fetch_headlines("SPY")
            headlines = snap.headlines
            news_sentiment = snap.overall_sentiment
            event_risk = snap.event_risk
            self.db.add(
                NewsSnapshot(
                    alert_id=alert_id,
                    headlines=headlines,
                    sentiment=news_sentiment,
                    event_risk=event_risk,
                )
            )

        ai_result: AIDecisionResponse
        if self.settings.enable_ai_filter:
            ai_result = self.ai.evaluate(alert, headlines, news_sentiment, event_risk, regime)
        else:
            from backend.schemas.alerts import Sentiment

            bias = (alert.bias or "").lower()
            direction = Direction.CALL if "bull" in bias else Direction.PUT if "bear" in bias else Direction.NONE
            try:
                sent = Sentiment(news_sentiment)
            except ValueError:
                sent = Sentiment.NEUTRAL
            ai_result = AIDecisionResponse(
                decision=Decision.APPROVE if direction != Direction.NONE else Decision.WAIT,
                direction=direction,
                confidence=0.5,
                reason_summary="Technical-only mode (AI filter disabled)",
                news_sentiment=sent,
                market_regime=regime,
                risk_flags=[],
                size_modifier=0.75,
            )

        self.db.add(
            AIDecisionRecord(
                alert_id=alert_id,
                decision=ai_result.decision.value,
                direction=ai_result.direction.value,
                confidence=ai_result.confidence,
                reason_summary=ai_result.reason_summary,
                news_sentiment=ai_result.news_sentiment.value,
                market_regime=ai_result.market_regime.value,
                risk_flags=ai_result.risk_flags,
                size_modifier=ai_result.size_modifier,
                full_response=ai_result.model_dump(),
            )
        )

        allowed, risk_reason, size_mod = self.risk.evaluate(alert, alert_id, ai_result.decision)
        size_mod *= ai_result.size_modifier

        execution_result = None
        rejection = None

        if not allowed:
            rejection = risk_reason
        elif ai_result.decision in (Decision.REJECT, Decision.WAIT):
            rejection = ai_result.reason_summary
        elif ai_result.decision == Decision.APPROVE or ai_result.decision == Decision.REDUCE_SIZE:
            price = alert.price or 500.0
            contract, opt_reason = self.options.select(ai_result.direction, price)
            if not contract:
                rejection = opt_reason
            else:
                qty = max(1, int(self.settings.max_capital_per_trade * size_mod / (contract.mid * 100)))
                execution_result = self.executor.execute(
                    alert_id=alert_id,
                    contract=contract,
                    direction=ai_result.direction,
                    quantity=qty,
                    decision=ai_result.decision,
                )
                self.db.add(
                    TradeExecution(
                        alert_id=alert_id,
                        action="BUY",
                        contract_symbol=contract.symbol,
                        quantity=qty,
                        fill_price=execution_result.get("fill_price", contract.mid),
                        mode=self.settings.execution_mode.value,
                        metadata_json=execution_result,
                    )
                )
                if execution_result.get("pnl") is not None:
                    self.risk.record_trade(execution_result["pnl"])

        rec = self.db.query(AlertRecord).filter(AlertRecord.alert_id == alert_id).first()
        if rec:
            rec.processed = True
            rec.normalized = alert.model_dump()
        self.db.commit()

        status = "approved" if execution_result else ("rejected" if rejection else "wait")
        return WebhookResponse(
            status=status,
            alert_id=alert_id,
            decision=ai_result,
            execution=execution_result,
            rejection_reason=rejection,
            latency_ms=(time.perf_counter() - start) * 1000,
        )
