from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import AIDecision, DecisionAction, Direction, NewsSentiment
from backend.services.risk_engine import RiskEngine


def test_kill_switch_rejects():
    RiskEngine._global_state.kill_switch = True
    engine = RiskEngine()
    alert = TradingViewAlert(ticker="SPY", bias="bullish", price=500.0)
    decision = AIDecision(
        decision=DecisionAction.APPROVE,
        direction=Direction.CALL,
        confidence=0.8,
        reason_summary="test",
        news_sentiment=NewsSentiment.BULLISH,
    )
    result, reasons = engine.evaluate(alert, decision, "test-id")
    assert result.decision == DecisionAction.REJECT
    assert "kill_switch_active" in reasons
    RiskEngine._global_state.kill_switch = False


def test_duplicate_alert_detection():
    engine = RiskEngine()
    assert engine.record_alert_seen("abc123") is False
    assert engine.record_alert_seen("abc123") is True
