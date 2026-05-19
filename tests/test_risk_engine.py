from datetime import datetime
from zoneinfo import ZoneInfo

from backend.config import Settings
from backend.schemas.alerts import TradingViewAlert
from backend.services.risk_engine import RiskEngine, RiskState


def _session_time() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    return now.strftime("%Y-%m-%dT%H:%M:%S%z")


def test_kill_switch_blocks():
    s = Settings(kill_switch=True)
    engine = RiskEngine(s)
    alert = TradingViewAlert(ticker="SPY", bias="bullish", time="2026-05-19T10:15:00-04:00")
    allowed, reason, _ = engine.evaluate(alert, "abc")
    assert not allowed
    assert reason == "KILL_SWITCH_ACTIVE"


def test_max_trades_blocks():
    s = Settings(max_trades_per_day=1)
    state = RiskState(trades_today=1)
    engine = RiskEngine(s, state, use_preset=False)
    alert = TradingViewAlert(ticker="SPY", bias="bullish", time="2026-05-19T10:15:00-04:00")
    allowed, reason, _ = engine.evaluate(alert, "x")
    assert not allowed
    assert reason == "MAX_TRADES_PER_DAY"
