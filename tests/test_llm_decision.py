from backend.schemas.alerts import Decision, Direction, MarketRegime, TradingViewAlert
from ai.llm_decision import MockDecisionEngine


def test_approve_aligned_bullish():
    engine = MockDecisionEngine()
    alert = TradingViewAlert(ticker="SPY", bias="bullish", action="buy")
    result = engine.evaluate(alert, [], "NEUTRAL", False, MarketRegime.TREND)
    assert result.decision == Decision.APPROVE
    assert result.direction == Direction.CALL


def test_wait_on_event_risk():
    engine = MockDecisionEngine()
    alert = TradingViewAlert(ticker="SPY", bias="bullish")
    result = engine.evaluate(alert, [], "MIXED", True, MarketRegime.EVENT_RISK)
    assert result.decision == Decision.WAIT
