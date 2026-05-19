from __future__ import annotations

from datetime import datetime, timezone

from backend.schemas.decision import DecisionResponse
from backend.schemas.tradingview import TradingViewAlert
from backend.services.market_context import MarketContextService
from backend.services.options_selector import OptionQuote, OptionsSelector
from backend.services.risk_engine import RiskEngine


def _alert(alert_time: datetime) -> TradingViewAlert:
    return TradingViewAlert.model_validate(
        {
            "ticker": "SPY",
            "time": alert_time.isoformat(),
            "price": 525.25,
            "interval": "1",
            "action": "BUY_CALL_SETUP",
            "market_position": "flat",
            "setup": "SPY_0DTE_SCALP",
            "bias": "bullish",
            "rsi": 58,
            "ema_fast": 526,
            "ema_slow": 524,
            "macd_state": "bullish",
            "volume_state": "spike",
            "vwap_state": "above",
            "atr": 0.9,
        }
    )


def _decision() -> DecisionResponse:
    return DecisionResponse(
        decision="APPROVE",
        direction="CALL",
        confidence=0.72,
        reason_summary="Supportive technical and news filter.",
        news_sentiment="BULLISH",
        market_regime="TREND",
        risk_flags=[],
        rejection_reasons=[],
        size_modifier=1.0,
    )


def test_risk_engine_approves_clean_market_hours_alert(settings, db_session) -> None:
    now = datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)
    engine = RiskEngine(settings, MarketContextService(settings), OptionsSelector(settings))

    result = engine.evaluate(db_session, _alert(now), _decision(), current_time=now)

    assert result.approved is True
    assert result.decision.decision == "APPROVE"


def test_risk_engine_rejects_stale_alert(settings, db_session) -> None:
    now = datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)
    stale = datetime(2026, 5, 19, 13, 0, tzinfo=timezone.utc)
    engine = RiskEngine(settings, MarketContextService(settings), OptionsSelector(settings))

    result = engine.evaluate(db_session, _alert(stale), _decision(), current_time=now)

    assert result.approved is False
    assert "STALE_ALERT" in result.decision.rejection_reasons


def test_risk_engine_rejects_wide_option_spread(settings, db_session) -> None:
    now = datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc)
    engine = RiskEngine(settings, MarketContextService(settings), OptionsSelector(settings))

    result = engine.evaluate(
        db_session,
        _alert(now),
        _decision(),
        option_quote=OptionQuote(bid=1.0, ask=1.8, delta=0.52, open_interest=1000, volume=500),
        current_time=now,
    )

    assert result.approved is False
    assert "OPTION_SPREAD_TOO_WIDE" in result.decision.rejection_reasons
