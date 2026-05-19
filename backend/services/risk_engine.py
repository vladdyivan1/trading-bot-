from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.models.entities import ExecutionRecord, RiskDailyState
from backend.schemas.decision import DecisionType
from backend.schemas.tradingview import TradingViewAlert
from backend.services.market_utils import ET, is_within_window, now_et, parse_hhmm
from backend.services.settings import settings


RISK_PRESETS: dict[str, dict[str, float | int]] = {
    "conservative": {
        "max_daily_loss": -500.0,
        "max_trades_per_day": 6,
        "max_consecutive_losses": 2,
        "max_capital_per_trade": 1_000.0,
        "max_total_exposure": 4_000.0,
    },
    "standard": {
        "max_daily_loss": -1_000.0,
        "max_trades_per_day": 12,
        "max_consecutive_losses": 3,
        "max_capital_per_trade": 1_500.0,
        "max_total_exposure": 8_000.0,
    },
    "aggressive": {
        "max_daily_loss": -1_750.0,
        "max_trades_per_day": 20,
        "max_consecutive_losses": 4,
        "max_capital_per_trade": 2_500.0,
        "max_total_exposure": 12_000.0,
    },
}


@dataclass(slots=True)
class RiskOutcome:
    allowed: bool
    decision: DecisionType
    reason: str
    size_modifier: float = 1.0
    risk_flags: list[str] | None = None


class RiskEngine:
    def __init__(self) -> None:
        preset = RISK_PRESETS.get(settings.risk_preset.lower(), RISK_PRESETS["standard"])
        self.max_daily_loss = float(preset["max_daily_loss"])
        self.max_trades_per_day = int(preset["max_trades_per_day"])
        self.max_consecutive_losses = int(preset["max_consecutive_losses"])
        self.max_capital_per_trade = float(preset["max_capital_per_trade"])
        self.max_total_exposure = float(preset["max_total_exposure"])

    def _get_daily_state(self, db: Session, trade_day: date) -> RiskDailyState:
        state = db.execute(select(RiskDailyState).where(RiskDailyState.trade_date == trade_day)).scalar_one_or_none()
        if state:
            return state
        state = RiskDailyState(trade_date=trade_day)
        db.add(state)
        db.flush()
        return state

    def _current_open_exposure(self, db: Session) -> float:
        stmt: Select[tuple[float]] = select(
            func.coalesce(func.sum(ExecutionRecord.entry_price * ExecutionRecord.quantity * 100), 0.0)
        ).where(ExecutionRecord.status == "OPEN")
        return float(db.execute(stmt).scalar_one())

    def _is_session_allowed(self, event_ts_et: datetime) -> bool:
        in_morning = is_within_window(event_ts_et, settings.session_morning_start, settings.session_morning_end)
        in_afternoon = settings.session_afternoon_enabled and is_within_window(
            event_ts_et,
            settings.session_afternoon_start,
            settings.session_afternoon_end,
        )
        return in_morning or in_afternoon

    def evaluate_pre_trade(
        self,
        db: Session,
        alert: TradingViewAlert,
        predicted_notional: float,
        event_risk_flags: list[str],
    ) -> RiskOutcome:
        now = datetime.now(UTC)
        event_time_utc = alert.event_time_utc()
        age_seconds = (now - event_time_utc).total_seconds()
        if age_seconds > settings.webhook_stale_seconds:
            return RiskOutcome(False, DecisionType.REJECT, "Stale alert rejected.", 0.0, ["STALE_ALERT"])

        if settings.hard_kill_switch:
            return RiskOutcome(False, DecisionType.REJECT, "Hard kill switch is enabled.", 0.0, ["KILL_SWITCH"])

        event_et = event_time_utc.astimezone(ET)
        if not self._is_session_allowed(event_et):
            return RiskOutcome(False, DecisionType.REJECT, "Outside configured trading session.", 0.0, ["OFF_SESSION"])

        if settings.reject_lunch_period and is_within_window(event_et, "11:30", "13:30"):
            return RiskOutcome(False, DecisionType.REJECT, "Lunch period filter active.", 0.0, ["LUNCH_FILTER"])

        if settings.no_trade_first_minutes > 0:
            open_dt = event_et.replace(hour=9, minute=30, second=0, microsecond=0)
            if event_et < (open_dt + timedelta(minutes=settings.no_trade_first_minutes)):
                return RiskOutcome(
                    False,
                    DecisionType.WAIT,
                    f"No trades in first {settings.no_trade_first_minutes} minutes after open.",
                    0.0,
                    ["OPENING_BUFFER"],
                )

        if settings.enforce_event_blackout and any(flag.startswith("EVENT:") for flag in event_risk_flags):
            return RiskOutcome(False, DecisionType.WAIT, "Macro event blackout window active.", 0.0, event_risk_flags)

        reject_after = parse_hhmm(settings.reject_after_time_et)
        if event_et.timetz().replace(tzinfo=None) >= reject_after:
            return RiskOutcome(False, DecisionType.REJECT, "Late-day theta decay guard triggered.", 0.0, ["THETA_GUARD"])

        state = self._get_daily_state(db, event_et.date())
        if state.kill_switch_engaged:
            return RiskOutcome(False, DecisionType.REJECT, "Daily kill switch engaged.", 0.0, ["KILL_SWITCH"])

        if state.realized_pnl <= self.max_daily_loss:
            state.kill_switch_engaged = True
            db.flush()
            return RiskOutcome(False, DecisionType.REJECT, "Max daily loss breached.", 0.0, ["MAX_DAILY_LOSS"])

        if state.trades_count >= self.max_trades_per_day:
            return RiskOutcome(False, DecisionType.REJECT, "Max trades per day reached.", 0.0, ["TRADE_CAP"])

        if state.consecutive_losses >= self.max_consecutive_losses:
            return RiskOutcome(
                False,
                DecisionType.WAIT,
                "Consecutive loss cooldown active.",
                0.0,
                ["LOSS_STREAK"],
            )

        if state.cooldown_until and now < state.cooldown_until:
            return RiskOutcome(False, DecisionType.WAIT, "Cooldown after stop-out is active.", 0.0, ["COOLDOWN"])

        if predicted_notional > self.max_capital_per_trade:
            return RiskOutcome(False, DecisionType.REDUCE_SIZE, "Per-trade capital cap exceeded.", 0.5, ["TRADE_SIZE_CAP"])

        current_exposure = self._current_open_exposure(db)
        if current_exposure + predicted_notional > self.max_total_exposure:
            return RiskOutcome(False, DecisionType.REJECT, "Max total exposure would be exceeded.", 0.0, ["EXPOSURE_CAP"])

        return RiskOutcome(True, DecisionType.APPROVE, "Risk checks passed.", 1.0, [])

    def register_open_trade(self, db: Session, event_time: datetime, notional: float) -> None:
        state = self._get_daily_state(db, event_time.astimezone(ET).date())
        state.trades_count += 1
        state.total_exposure += notional
        db.flush()

    def register_closed_trade(self, db: Session, event_time: datetime, pnl: float) -> None:
        state = self._get_daily_state(db, event_time.astimezone(ET).date())
        state.realized_pnl += pnl
        state.total_exposure = max(0.0, state.total_exposure - abs(pnl))
        if pnl < 0:
            state.consecutive_losses += 1
            state.cooldown_until = datetime.now(UTC) + timedelta(minutes=settings.cooldown_minutes_after_loss)
        else:
            state.consecutive_losses = 0
        if state.realized_pnl <= self.max_daily_loss:
            state.kill_switch_engaged = True
        db.flush()
