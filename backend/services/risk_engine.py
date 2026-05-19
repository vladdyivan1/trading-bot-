"""Strict 0DTE scalping risk controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.models import Alert, Decision, Order, Position
from backend.schemas.decision import DecisionResponse
from backend.schemas.tradingview import TradingViewAlert
from backend.services.market_context import MarketContextService
from backend.services.options_selector import OptionQuote, OptionsSelector


@dataclass(frozen=True)
class RiskPreset:
    max_daily_loss: float
    max_trades_per_day: int
    max_consecutive_losses: int
    max_capital_at_risk_per_trade: float
    max_total_exposure: float
    confidence_floor: float


PRESETS = {
    "conservative": RiskPreset(300.0, 4, 2, 200.0, 500.0, 0.68),
    "standard": RiskPreset(500.0, 8, 3, 350.0, 1000.0, 0.58),
    "aggressive": RiskPreset(900.0, 14, 4, 600.0, 1800.0, 0.50),
}


@dataclass(frozen=True)
class RiskEvaluation:
    approved: bool
    decision: DecisionResponse


class RiskEngine:
    def __init__(
        self,
        settings: Settings,
        market_context: MarketContextService,
        options_selector: OptionsSelector,
    ) -> None:
        self.settings = settings
        self.market_context = market_context
        self.options_selector = options_selector
        self.preset = PRESETS[settings.risk_preset]

    def evaluate(
        self,
        db: Session,
        alert: TradingViewAlert,
        decision: DecisionResponse,
        option_quote: OptionQuote | None = None,
        current_time: datetime | None = None,
    ) -> RiskEvaluation:
        now = current_time or datetime.now(timezone.utc)
        rejections: list[str] = list(decision.rejection_reasons)
        risk_flags = list(dict.fromkeys(decision.risk_flags))

        if self.settings.kill_switch:
            rejections.append("KILL_SWITCH_ACTIVE")
        if alert.ticker not in self.settings.allowed_symbols:
            rejections.append("SYMBOL_NOT_ALLOWED")
        if self.market_context.alert_age_seconds(alert, now) > self.settings.stale_alert_seconds:
            rejections.append("STALE_ALERT")

        session = self.market_context.session_state(now)
        if not session.is_open:
            rejections.append(session.reason)

        key = alert.idempotency_key()
        duplicate = db.scalar(select(Alert).where(Alert.idempotency_key == key))
        if duplicate is not None:
            rejections.append("DUPLICATE_ALERT")
        else:
            recent_cutoff = now - timedelta(seconds=self.settings.duplicate_alert_window_seconds)
            recent_duplicate = db.scalar(
                select(Alert).where(
                    Alert.ticker == alert.ticker,
                    Alert.bias == alert.bias,
                    Alert.setup == alert.setup,
                    Alert.received_at >= recent_cutoff,
                )
            )
            if recent_duplicate is not None:
                rejections.append("RECENT_DUPLICATE_ALERT")

        daily_pnl = self._daily_realized_pnl(db, now)
        if daily_pnl <= -min(self.settings.max_daily_loss, self.preset.max_daily_loss):
            rejections.append("DAILY_LOSS_LIMIT_HIT")
        if self._daily_trade_count(db, now) >= min(self.settings.max_trades_per_day, self.preset.max_trades_per_day):
            rejections.append("MAX_TRADES_PER_DAY")
        if self._consecutive_losses(db) >= min(
            self.settings.max_consecutive_losses, self.preset.max_consecutive_losses
        ):
            rejections.append("MAX_CONSECUTIVE_LOSSES")
        if self._open_exposure(db) >= min(self.settings.max_total_exposure, self.preset.max_total_exposure):
            rejections.append("MAX_TOTAL_EXPOSURE")
        if decision.confidence < self.preset.confidence_floor and decision.decision == "APPROVE":
            rejections.append("CONFIDENCE_BELOW_PRESET_FLOOR")

        rejections.extend(self.options_selector.liquidity_rejections(option_quote))

        final_decision = decision.decision
        size_modifier = decision.size_modifier
        approved = not rejections and final_decision in {"APPROVE", "REDUCE_SIZE"} and size_modifier > 0
        if rejections:
            final_decision = "REJECT"
            size_modifier = 0.0
        elif final_decision == "APPROVE" and size_modifier < 1.0:
            final_decision = "REDUCE_SIZE"

        risk_adjusted = decision.model_copy(
            update={
                "decision": final_decision,
                "risk_flags": risk_flags,
                "rejection_reasons": list(dict.fromkeys(rejections)),
                "size_modifier": size_modifier,
            }
        )
        return RiskEvaluation(approved=approved, decision=risk_adjusted)

    @staticmethod
    def _day_bounds(now: datetime) -> tuple[datetime, datetime]:
        start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    def _daily_realized_pnl(self, db: Session, now: datetime) -> float:
        start, end = self._day_bounds(now)
        value = db.scalar(
            select(func.coalesce(func.sum(Order.realized_pnl), 0.0)).where(
                Order.created_at >= start,
                Order.created_at < end,
            )
        )
        return float(value or 0.0)

    def _daily_trade_count(self, db: Session, now: datetime) -> int:
        start, end = self._day_bounds(now)
        value = db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= start, Order.created_at < end)
        )
        return int(value or 0)

    def _consecutive_losses(self, db: Session) -> int:
        orders = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(10)).all()
        count = 0
        for order in orders:
            if order.realized_pnl < 0:
                count += 1
            else:
                break
        return count

    def _open_exposure(self, db: Session) -> float:
        value = db.scalar(
            select(func.coalesce(func.sum(Position.entry_price * Position.quantity * 100), 0.0)).where(
                Position.status == "OPEN"
            )
        )
        return float(value or 0.0)
