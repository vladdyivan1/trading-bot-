import pytest

from ai.llm_decision import RuleBasedDecisionEngine
from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import DecisionAction, MarketRegime


@pytest.mark.asyncio
async def test_rule_engine_approves_aligned_bullish():
    engine = RuleBasedDecisionEngine()
    alert = TradingViewAlert(ticker="SPY", bias="bullish", price=500.0, action="buy")
    headlines = [{"title": "S&P 500 rally continues", "score": 0.6}]
    decision = await engine.evaluate(alert, headlines, MarketRegime.TREND, False)
    assert decision.direction.value == "CALL"
    assert decision.decision in (DecisionAction.APPROVE, DecisionAction.REDUCE_SIZE)


@pytest.mark.asyncio
async def test_event_risk_waits():
    engine = RuleBasedDecisionEngine()
    alert = TradingViewAlert(ticker="SPY", bias="bullish", price=500.0)
    headlines = [{"title": "FOMC rate decision at 2pm", "score": 0}]
    decision = await engine.evaluate(alert, headlines, MarketRegime.EVENT_RISK, True)
    assert decision.decision == DecisionAction.WAIT
