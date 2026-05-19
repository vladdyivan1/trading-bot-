from __future__ import annotations

from datetime import datetime, timezone

from ai.news_providers import NewsHeadline
from backend.schemas.tradingview import TradingViewAlert
from backend.services.decision_service import DecisionService


class BullishNewsProvider:
    def latest_headlines(self, query_terms: list[str], limit: int = 25) -> list[NewsHeadline]:
        return [
            NewsHeadline(
                title="S&P 500 rally as lower yields lift mega-cap technology shares",
                published_at=datetime.now(timezone.utc),
            )
        ]


def test_decision_service_processes_and_idempotently_replays(settings, db_session) -> None:
    settings.market_timezone = "UTC"
    settings.morning_start = "00:00"
    settings.morning_end = "23:57"
    settings.no_trade_lunch_start = "23:58"
    settings.no_trade_lunch_end = "23:59"
    service = DecisionService(settings)
    service.news_provider = BullishNewsProvider()
    now = datetime.now(timezone.utc)
    payload = {
        "ticker": "SPY",
        "time": now.isoformat(),
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

    first = service.process(db_session, TradingViewAlert.model_validate(payload))
    second = service.process(db_session, TradingViewAlert.model_validate(payload))

    assert first.alert_id == second.alert_id
    assert first.response.decision in {"APPROVE", "REDUCE_SIZE"}
    assert second.response.rejection_reasons[0] == "IDEMPOTENT_REPLAY"
    assert first.execution is not None
    assert first.execution.status == "FILLED"
