"""Strict risk filters for 0DTE scalping."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from backend.config import Settings, apply_risk_preset
from backend.schemas.alerts import Decision, TradingViewAlert
from backend.services.alert_normalizer import parse_alert_time
from backend.services.session_service import (
    in_session_window,
    is_late_day,
    is_opening_skip,
    now_et,
)


@dataclass
class RiskState:
    daily_pnl: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    last_stop_at: Optional[datetime] = None
    recent_alert_times: list[datetime] = field(default_factory=list)
    trading_halted: bool = False


class RiskEngine:
    def __init__(self, settings: Settings, state: Optional[RiskState] = None, use_preset: bool = True):
        self.settings = apply_risk_preset(settings) if use_preset else settings
        self.state = state or RiskState()

    def evaluate(
        self,
        alert: TradingViewAlert,
        alert_id: str,
        ai_decision: Optional[Decision] = None,
    ) -> tuple[bool, str, float]:
        """
        Returns (allowed, rejection_reason, size_modifier).
        size_modifier may be reduced by risk rules.
        """
        if self.settings.kill_switch:
            return False, "KILL_SWITCH_ACTIVE", 0.0

        if self.state.trading_halted:
            return False, "DAILY_TRADING_HALTED", 0.0

        if self.state.daily_pnl <= -self.settings.max_daily_loss:
            self.state.trading_halted = True
            return False, "MAX_DAILY_LOSS_REACHED", 0.0

        if self.state.trades_today >= self.settings.max_trades_per_day:
            return False, "MAX_TRADES_PER_DAY", 0.0

        if self.state.consecutive_losses >= self.settings.max_consecutive_losses:
            return False, "MAX_CONSECUTIVE_LOSSES", 0.0

        alert_time = parse_alert_time(alert.time) or now_et()
        if not in_session_window(
            alert_time,
            self.settings.session_am_start,
            self.settings.session_am_end,
            self.settings.session_pm_start,
            self.settings.session_pm_end,
            self.settings.enable_pm_session,
            self.settings.lunch_start,
            self.settings.lunch_end,
        ):
            return False, "OUTSIDE_SESSION_WINDOW", 0.0

        if is_opening_skip(self.settings.skip_first_minutes_after_open, alert_time):
            return False, "OPENING_SKIP_PERIOD", 0.0

        if is_late_day(self.settings.reject_late_day_minutes, alert_time):
            return False, "LATE_DAY_THETA_RISK", 0.0

        age = (now_et() - alert_time.replace(tzinfo=now_et().tzinfo) if alert_time.tzinfo else now_et() - alert_time).total_seconds()
        if age > self.settings.stale_alert_max_seconds:
            return False, "STALE_ALERT", 0.0

        window = timedelta(seconds=self.settings.duplicate_alert_window_seconds)
        cutoff = now_et() - window
        recent = [t for t in self.state.recent_alert_times if t > cutoff]
        if len(recent) >= 1:
            return False, "DUPLICATE_ALERT_WINDOW", 0.0

        if self.state.last_stop_at:
            cooldown = timedelta(seconds=self.settings.cooldown_after_stop_seconds)
            if now_et() - self.state.last_stop_at.replace(tzinfo=now_et().tzinfo if self.state.last_stop_at.tzinfo is None else None) < cooldown:
                return False, "COOLDOWN_AFTER_STOP", 0.0

        size_mod = 1.0
        if ai_decision == Decision.REDUCE_SIZE:
            size_mod = 0.5

        self.state.recent_alert_times.append(now_et())
        return True, "", size_mod

    def record_trade(self, pnl: float) -> None:
        self.state.trades_today += 1
        self.state.daily_pnl += pnl
        if pnl < 0:
            self.state.consecutive_losses += 1
            if pnl < -50:
                self.state.last_stop_at = now_et()
        else:
            self.state.consecutive_losses = 0
