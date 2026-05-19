from __future__ import annotations

from datetime import UTC, datetime

from backend.schemas.decision import DecisionType
from backend.schemas.tradingview import TradingViewAlert
from backend.services.risk_engine import RiskEngine
from backend.services.settings import settings


def test_risk_engine_rejects_stale_alert(db_session) -> None:
    settings.webhook_stale_seconds = 1
    engine = RiskEngine()
    alert = TradingViewAlert(
        ticker="SPY",
        time=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        price=500.0,
        interval="1",
        action="BUY_CALL",
        bias="bullish",
    )
    outcome = engine.evaluate_pre_trade(db_session, alert, predicted_notional=100, event_risk_flags=[])
    assert not outcome.allowed
    assert outcome.decision == DecisionType.REJECT
