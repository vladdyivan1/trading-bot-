"""Strict risk filters for 0DTE options scalping."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.config import RISK_PRESETS, Settings, get_settings
from backend.schemas.alerts import TradingViewAlert
from backend.schemas.decisions import AIDecision, DecisionAction
from backend.services.session_service import (
    is_major_release_window,
    is_trading_session,
    minutes_since_open,
    minutes_to_close,
    now_et,
)


@dataclass
class RiskState:
    daily_pnl: float = 0.0
    trades_today: int = 0
    consecutive_losses: int = 0
    last_stop_at: datetime | None = None
    last_alert_at: datetime | None = None
    last_alert_hash: str | None = None
    kill_switch: bool = False


class RiskEngine:
    """In-memory risk state; production can persist to Redis/DB."""

    _global_state = RiskState()

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.preset = RISK_PRESETS.get(self.settings.risk_preset, RISK_PRESETS["standard"])

    @classmethod
    def get_state(cls) -> RiskState:
        return cls._global_state

    def evaluate(
        self,
        alert: TradingViewAlert,
        decision: AIDecision,
        alert_id: str,
        alert_time: datetime | None = None,
    ) -> tuple[AIDecision, list[str]]:
        rejections: list[str] = []
        state = self._global_state

        if self.settings.kill_switch or state.kill_switch:
            rejections.append("kill_switch_active")
            return self._reject(decision, rejections), rejections

        if state.daily_pnl <= -self.preset["max_daily_loss"]:
            rejections.append("max_daily_loss_reached")
            return self._reject(decision, rejections), rejections

        if state.trades_today >= self.preset["max_trades_per_day"]:
            rejections.append("max_trades_per_day")
            return self._reject(decision, rejections), rejections

        if state.consecutive_losses >= self.preset["max_consecutive_losses"]:
            rejections.append("max_consecutive_losses")
            return self._reject(decision, rejections), rejections

        if state.last_stop_at:
            cooldown = timedelta(seconds=self.settings.cooldown_after_stop_seconds)
            if now_et().replace(tzinfo=None) < state.last_stop_at + cooldown:
                rejections.append("cooldown_after_stop")
                return self._reject(decision, rejections), rejections

        at = alert_time or alert.parsed_time() or now_et()
        if at.tzinfo:
            at = at.replace(tzinfo=None)

        if not is_trading_session(at.replace(tzinfo=now_et().tzinfo) if at.tzinfo is None else at):
            rejections.append("outside_trading_session")
            return self._reject(decision, rejections), rejections

        if self.settings.skip_first_minutes_after_open > 0:
            if minutes_since_open(at.replace(tzinfo=now_et().tzinfo)) < self.settings.skip_first_minutes_after_open:
                rejections.append("skip_first_minutes_after_open")
                return self._reject(decision, rejections), rejections

        if self.settings.block_major_releases and is_major_release_window(at.replace(tzinfo=now_et().tzinfo)):
            rejections.append("major_economic_release_window")
            return self._reject(decision, rejections), rejections

        if self.settings.stale_alert_seconds > 0 and alert.parsed_time():
            age = (now_et() - alert.parsed_time().replace(tzinfo=now_et().tzinfo)).total_seconds()
            if age > self.settings.stale_alert_seconds:
                rejections.append("stale_alert")
                return self._reject(decision, rejections), rejections

        if minutes_to_close(at.replace(tzinfo=now_et().tzinfo)) < self.settings.reject_late_day_minutes_before_close:
            rejections.append("late_day_theta_risk")
            return self._reject(decision, rejections), rejections

        if decision.confidence < self.preset["min_confidence_approve"]:
            if decision.decision == DecisionAction.APPROVE:
                decision.decision = DecisionAction.WAIT
                rejections.append("confidence_below_threshold")

        if decision.decision == DecisionAction.APPROVE:
            cap = self.preset["size_modifier_cap"]
            decision.size_modifier = min(decision.size_modifier, cap)

        return decision, rejections

    def record_trade(self, pnl: float) -> None:
        state = self._global_state
        state.trades_today += 1
        state.daily_pnl += pnl
        if pnl < 0:
            state.consecutive_losses += 1
            state.last_stop_at = datetime.utcnow()
        else:
            state.consecutive_losses = 0

    def record_alert_seen(self, alert_id: str) -> bool:
        """Return True if duplicate within window."""
        state = self._global_state
        now = datetime.utcnow()
        if (
            state.last_alert_hash == alert_id
            and state.last_alert_at
            and (now - state.last_alert_at).total_seconds()
            < self.settings.duplicate_alert_window_seconds
        ):
            return True
        state.last_alert_hash = alert_id
        state.last_alert_at = now
        return False

    def reset_daily(self) -> None:
        s = self._global_state
        s.daily_pnl = 0.0
        s.trades_today = 0
        s.consecutive_losses = 0

    @staticmethod
    def _reject(decision: AIDecision, reasons: list[str]) -> AIDecision:
        decision.decision = DecisionAction.REJECT
        decision.risk_flags = list(set(decision.risk_flags + reasons))
        return decision
