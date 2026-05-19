"""Market session and lightweight regime classification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from backend.config import Settings
from backend.schemas.tradingview import TradingViewAlert


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(int(hour), int(minute))


@dataclass(frozen=True)
class SessionState:
    now_et: datetime
    is_open: bool
    reason: str


class MarketContextService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tz = ZoneInfo(settings.market_timezone)

    def session_state(self, current_time: datetime | None = None) -> SessionState:
        now = current_time or datetime.now(timezone.utc)
        now_et = now.astimezone(self.tz)
        if now_et.weekday() >= 5:
            return SessionState(now_et=now_et, is_open=False, reason="WEEKEND")

        current = now_et.time()
        morning = _parse_hhmm(self.settings.morning_start) <= current <= _parse_hhmm(self.settings.morning_end)
        afternoon = (
            self.settings.enable_afternoon_session
            and _parse_hhmm(self.settings.afternoon_start) <= current <= _parse_hhmm(self.settings.afternoon_end)
        )
        lunch = _parse_hhmm(self.settings.no_trade_lunch_start) <= current <= _parse_hhmm(self.settings.no_trade_lunch_end)
        if lunch:
            return SessionState(now_et=now_et, is_open=False, reason="LUNCH_BLOCK")
        if morning or afternoon:
            return SessionState(now_et=now_et, is_open=True, reason="SESSION_OPEN")
        return SessionState(now_et=now_et, is_open=False, reason="OUTSIDE_SESSION")

    def alert_age_seconds(self, alert: TradingViewAlert, current_time: datetime | None = None) -> float:
        now = current_time or datetime.now(timezone.utc)
        alert_time = alert.time if alert.time.tzinfo else alert.time.replace(tzinfo=timezone.utc)
        return abs((now - alert_time.astimezone(timezone.utc)).total_seconds())

    def classify_regime(self, alert: TradingViewAlert, risk_flags: list[str] | None = None) -> str:
        flags = set(risk_flags or [])
        if "EVENT_RISK_HEADLINES" in flags:
            return "EVENT_RISK"

        atr_ratio = (alert.atr or 0.0) / alert.price if alert.price else 0.0
        if atr_ratio >= 0.004:
            return "HIGH_VOL"

        trend_aligned = (
            (alert.bias == "bullish" and (alert.ema_fast or 0) > (alert.ema_slow or 0) and alert.vwap_state == "above")
            or (alert.bias == "bearish" and (alert.ema_fast or 0) < (alert.ema_slow or 0) and alert.vwap_state == "below")
        )
        momentum = (
            (alert.bias == "bullish" and alert.macd_state == "bullish")
            or (alert.bias == "bearish" and alert.macd_state == "bearish")
        )
        if trend_aligned and momentum:
            return "TREND"
        return "CHOP"
