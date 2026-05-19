"""End-to-end TradingView webhook decision pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.llm_decision import LlmDecisionEngine
from ai.news_providers import build_news_provider
from ai.sentiment_engine import NewsAnalysis, SentimentEngine
from backend.config import Settings, get_settings
from backend.models import Alert, Decision, NewsSnapshot
from backend.schemas.decision import DecisionEnvelope, DecisionResponse, ExecutionResult
from backend.schemas.tradingview import TradingViewAlert
from backend.services.market_context import MarketContextService
from backend.services.options_selector import OptionsSelector
from backend.services.risk_engine import RiskEngine
from execution.broker_base import OrderRequest
from execution.paper_executor import PaperExecutor


class DecisionService:
    """Coordinates validation, enrichment, AI scoring, risk checks, and execution."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.news_provider = build_news_provider(self.settings.news_provider, self.settings.news_rss_urls)
        self.sentiment_engine = SentimentEngine()
        self.llm_engine = LlmDecisionEngine()
        self.market_context = MarketContextService(self.settings)
        self.options_selector = OptionsSelector(self.settings)
        self.risk_engine = RiskEngine(self.settings, self.market_context, self.options_selector)
        self.paper_executor = PaperExecutor()

    def process(self, db: Session, alert: TradingViewAlert) -> DecisionEnvelope:
        existing = self._existing_decision(db, alert)
        if existing is not None:
            return existing

        headlines = []
        if self.settings.enable_news_filter:
            headlines = self.news_provider.latest_headlines(
                [
                    "SPY",
                    "S&P 500",
                    "Federal Reserve",
                    "CPI",
                    "jobs",
                    "unemployment",
                    "Treasury yields",
                    "mega-cap earnings",
                ]
            )
            news = self.sentiment_engine.analyze(headlines)
        else:
            news = NewsAnalysis(
                sentiment="NEUTRAL",
                summary="News filter disabled by feature flag.",
                risk_flags=["NEWS_FILTER_DISABLED"],
            )

        market_regime = self.market_context.classify_regime(alert, news.risk_flags)
        if self.settings.enable_ai_filter:
            decision = self.llm_engine.decide(
                alert,
                news,
                market_regime,
                {
                    "ai_filter": self.settings.enable_ai_filter,
                    "news_filter": self.settings.enable_news_filter,
                    "broker_execution": self.settings.enable_broker_execution,
                },
            )
        else:
            decision = DecisionResponse(
                decision="APPROVE",
                direction=alert.direction,
                confidence=0.50,
                reason_summary="AI filter disabled; using technical setup and risk engine only.",
                news_sentiment=news.sentiment,
                market_regime=market_regime,
                risk_flags=["AI_FILTER_DISABLED", *news.risk_flags],
                rejection_reasons=[],
                size_modifier=0.75,
            )

        contract = self.options_selector.select_contract(alert.ticker, alert.price, decision.direction)
        risk = self.risk_engine.evaluate(db, alert, decision, option_quote=contract.quote)
        final_decision = risk.decision

        alert_model = Alert(
            idempotency_key=alert.idempotency_key(),
            ticker=alert.ticker,
            alert_time=alert.time,
            received_at=datetime.now(timezone.utc),
            price=alert.price,
            interval=alert.interval,
            action=alert.action,
            bias=alert.bias,
            setup=alert.setup,
            payload=alert.raw_payload or alert.model_dump(mode="json"),
        )
        news_model = NewsSnapshot(
            created_at=datetime.now(timezone.utc),
            sentiment=news.sentiment,
            summary=news.summary,
            risk_flags=news.risk_flags,
            headlines=[score.model_dump() for score in news.headline_scores],
        )
        db.add(alert_model)
        db.add(news_model)
        db.flush()

        decision_model = Decision(
            alert_id=alert_model.id,
            news_snapshot_id=news_model.id,
            created_at=datetime.now(timezone.utc),
            decision=final_decision.decision,
            direction=final_decision.direction,
            confidence=final_decision.confidence,
            reason_summary=final_decision.reason_summary,
            news_sentiment=final_decision.news_sentiment,
            market_regime=final_decision.market_regime,
            risk_flags=final_decision.risk_flags,
            rejection_reasons=final_decision.rejection_reasons,
            size_modifier=final_decision.size_modifier,
            approved=risk.approved,
            payload={
                "selected_contract": contract.__dict__,
                "feature_flags": {
                    "enable_ai_filter": self.settings.enable_ai_filter,
                    "enable_news_filter": self.settings.enable_news_filter,
                    "enable_broker_execution": self.settings.enable_broker_execution,
                    "paper_trading": self.settings.paper_trading,
                },
            },
        )
        db.add(decision_model)
        db.flush()

        execution: ExecutionResult | None = None
        if risk.approved:
            request = self._build_order_request(contract, alert, final_decision)
            execution = self.paper_executor.submit_order(request)
            self.paper_executor.persist_fill(db, decision_model.id, request, execution)

        db.commit()
        db.refresh(alert_model)
        db.refresh(decision_model)
        return DecisionEnvelope(
            alert_id=alert_model.id,
            decision_id=decision_model.id,
            received_at=alert_model.received_at,
            response=final_decision,
            execution=execution,
        )

    def _existing_decision(self, db: Session, alert: TradingViewAlert) -> DecisionEnvelope | None:
        alert_model = db.scalar(select(Alert).where(Alert.idempotency_key == alert.idempotency_key()))
        if alert_model is None:
            return None
        decision_model = db.scalar(
            select(Decision).where(Decision.alert_id == alert_model.id).order_by(Decision.created_at.desc())
        )
        if decision_model is None:
            return None
        response = DecisionResponse(
            decision=decision_model.decision,
            direction=decision_model.direction,
            confidence=decision_model.confidence,
            reason_summary=decision_model.reason_summary,
            news_sentiment=decision_model.news_sentiment,
            market_regime=decision_model.market_regime,
            risk_flags=decision_model.risk_flags,
            rejection_reasons=["IDEMPOTENT_REPLAY", *decision_model.rejection_reasons],
            size_modifier=decision_model.size_modifier,
        )
        return DecisionEnvelope(
            alert_id=alert_model.id,
            decision_id=decision_model.id,
            received_at=alert_model.received_at,
            response=response,
            execution=None,
        )

    def _build_order_request(
        self,
        contract,
        alert: TradingViewAlert,
        decision: DecisionResponse,
    ) -> OrderRequest:
        synthetic_price = max(0.05, round(alert.price * 0.01, 2))
        contract_risk = synthetic_price * 100
        capital = min(
            self.settings.max_capital_at_risk_per_trade,
            self.risk_engine.preset.max_capital_at_risk_per_trade,
        )
        quantity = max(1, int((capital * decision.size_modifier) // contract_risk))
        return OrderRequest(
            contract=contract,
            side="BUY",
            quantity=quantity,
            max_price=synthetic_price,
            metadata={
                "underlying_price": alert.price,
                "source": "tradingview",
                "setup": alert.setup,
                "decision": decision.decision,
            },
        )
