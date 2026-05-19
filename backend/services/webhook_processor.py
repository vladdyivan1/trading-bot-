"""Orchestrates alert ingestion, AI filter, risk, and execution."""
import logging
from typing import Any

from backend.config import get_settings
from backend.schemas.alerts import TradingViewAlert, WebhookResponse
from backend.schemas.decisions import AIDecision, DecisionAction, Direction
from backend.services.alert_store import AlertStore, make_alert_id
from backend.services.options_selector import OptionsSelector
from backend.services.regime_classifier import classify_regime
from backend.services.risk_engine import RiskEngine
from backend.services.session_service import time_of_day_bucket
from ai.llm_decision import get_decision_engine
from ai.news_providers import get_news_provider
from execution.paper_executor import PaperExecutor
from execution.broker_base import get_executor

logger = logging.getLogger(__name__)


class WebhookProcessor:
    def __init__(self, store: AlertStore):
        self.store = store
        self.settings = get_settings()
        self.risk = RiskEngine()
        self.options = OptionsSelector()
        self.decision_engine = get_decision_engine()
        self.news_provider = get_news_provider()

    async def process(self, raw: dict[str, Any]) -> WebhookResponse:
        alert = TradingViewAlert.model_validate({**raw, "raw_payload": raw})
        alert_id = make_alert_id(raw)

        if self.risk.record_alert_seen(alert_id):
            return WebhookResponse(
                status="duplicate",
                decision="REJECT",
                direction="NONE",
                confidence=0.0,
                reason_summary="Duplicate alert within dedup window",
                rejection_reasons=["duplicate_alert"],
            )

        await self.store.save_alert(alert, raw, alert_id)

        regime = classify_regime(alert)
        headlines: list[dict] = []
        event_risk = False

        if self.settings.enable_news_filter:
            bundle = await self.news_provider.fetch_headlines("SPY")
            headlines = bundle.headlines
            event_risk = bundle.event_risk
            await self.store.save_news(alert_id, headlines, bundle.sentiment, event_risk)

        if self.settings.enable_ai_filter:
            decision = await self.decision_engine.evaluate(alert, headlines, regime, event_risk)
        else:
            decision = self._technical_only(alert, regime)

        decision.market_regime = regime
        decision, risk_rejections = self.risk.evaluate(alert, decision, alert_id)

        rejection_reasons = list(risk_rejections)
        execution_id = None

        if decision.decision in (DecisionAction.APPROVE, DecisionAction.REDUCE_SIZE):
            price = alert.price or 500.0
            contract = self.options.select_contract(price, decision.direction)
            if contract:
                spread_issues = self.options.validate_contract(contract)
                if spread_issues:
                    decision.decision = DecisionAction.REJECT
                    rejection_reasons.extend(spread_issues)
                else:
                    executor = get_executor()
                    qty = max(1, int(1 * decision.size_modifier))
                    result = await executor.open_position(
                        contract, qty, decision.size_modifier
                    )
                    if result.success:
                        execution_id = result.order_id
                        bucket = time_of_day_bucket()
                        await self.store.save_position(alert_id, result, bucket)
                    else:
                        rejection_reasons.append(result.message)
                        decision.decision = DecisionAction.REJECT

        await self.store.save_decision(alert_id, decision, rejection_reasons)
        await self.store.mark_processed(alert_id)

        return WebhookResponse(
            status="ok",
            decision=decision.decision.value,
            direction=decision.direction.value,
            confidence=decision.confidence,
            reason_summary=decision.reason_summary,
            execution_id=execution_id,
            rejection_reasons=rejection_reasons,
        )

    def _technical_only(self, alert: TradingViewAlert, regime) -> AIDecision:
        from backend.schemas.decisions import MarketRegime, NewsSentiment

        direction = Direction.CALL if alert.is_bullish else Direction.PUT if alert.is_bearish else Direction.NONE
        return AIDecision(
            decision=DecisionAction.APPROVE if direction != Direction.NONE else DecisionAction.WAIT,
            direction=direction,
            confidence=0.45,
            reason_summary="Technical-only mode (AI/news disabled); probabilistic filter only.",
            news_sentiment=NewsSentiment.NEUTRAL,
            market_regime=regime if isinstance(regime, MarketRegime) else MarketRegime.TREND,
            technical_only=True,
            size_modifier=0.5,
        )
