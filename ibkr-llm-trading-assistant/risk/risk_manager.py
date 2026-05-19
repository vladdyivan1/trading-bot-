"""Deterministic risk engine — blocks unsafe trades."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from loguru import logger

from config.settings import Settings, get_settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import size_by_risk
from schemas import LLMRecommendation, RiskCheckResult, TradeSignal


@dataclass
class RiskState:
    """Tracks intraday / weekly risk usage."""

    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    trades_today: int = 0
    peak_equity: float = 0.0
    current_equity: float = 100_000.0
    open_positions: int = 0
    last_reset: date = field(default_factory=date.today)


class RiskManager:
    """Hard-coded risk checks — LLM cannot bypass this layer."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.kill_switch = KillSwitch(self.settings)
        self.state = RiskState(current_equity=100_000.0, peak_equity=100_000.0)

    def update_equity(self, equity: float) -> None:
        self._maybe_reset_daily()
        self.state.current_equity = equity
        self.state.peak_equity = max(self.state.peak_equity, equity)

    def record_trade_pnl(self, pnl: float) -> None:
        self._maybe_reset_daily()
        self.state.daily_pnl += pnl
        self.state.weekly_pnl += pnl
        self.state.trades_today += 1

    def _maybe_reset_daily(self) -> None:
        today = date.today()
        if self.state.last_reset != today:
            self.state.daily_pnl = 0.0
            self.state.trades_today = 0
            if today.weekday() == 0:
                self.state.weekly_pnl = 0.0
            self.state.last_reset = today

    def validate(
        self,
        signal: TradeSignal,
        llm: LLMRecommendation | None = None,
        backtest_trades: int = 0,
        spread_pct: float = 0.0,
        human_approved_live: bool = False,
    ) -> RiskCheckResult:
        """Run all risk checks. Returns approval with optional adjusted quantity."""
        reasons: list[str] = []

        if self.kill_switch.is_active:
            reasons.append("Kill switch is active")

        if not self.settings.paper_trading and not self.settings.live_trading_enabled:
            reasons.append("Live trading is disabled")

        if not self.settings.paper_trading and self.settings.live_trading_enabled:
            if not human_approved_live:
                reasons.append("Live trading requires explicit human approval")

        if signal.confidence_score < self.settings.min_model_confidence:
            reasons.append(
                f"Confidence {signal.confidence_score:.2f} below minimum "
                f"{self.settings.min_model_confidence}"
            )

        if signal.reward_to_risk < self.settings.min_reward_to_risk:
            reasons.append(
                f"R:R {signal.reward_to_risk:.2f} below minimum {self.settings.min_reward_to_risk}"
            )

        if backtest_trades < self.settings.min_backtest_trades:
            reasons.append(
                f"Backtest sample {backtest_trades} < {self.settings.min_backtest_trades}"
            )

        if spread_pct > self.settings.max_spread_pct:
            reasons.append(f"Spread {spread_pct:.2f}% exceeds max {self.settings.max_spread_pct}%")

        if self.state.open_positions >= self.settings.max_open_positions:
            reasons.append(f"Max open positions ({self.settings.max_open_positions}) reached")

        if self.state.trades_today >= self.settings.max_trades_per_day:
            reasons.append(f"Max trades per day ({self.settings.max_trades_per_day}) reached")

        equity = self.state.current_equity
        if equity > 0:
            daily_loss_pct = -self.state.daily_pnl / equity * 100
            if self.state.daily_pnl < 0 and daily_loss_pct >= self.settings.max_daily_loss_pct:
                reasons.append(f"Max daily loss exceeded ({daily_loss_pct:.2f}%)")

            weekly_loss_pct = -self.state.weekly_pnl / equity * 100
            if self.state.weekly_pnl < 0 and weekly_loss_pct >= self.settings.max_weekly_loss_pct:
                reasons.append(f"Max weekly loss exceeded ({weekly_loss_pct:.2f}%)")

            if self.state.peak_equity > 0:
                dd = (self.state.peak_equity - equity) / self.state.peak_equity * 100
                if dd >= self.settings.max_account_drawdown_pct:
                    reasons.append(f"Max account drawdown exceeded ({dd:.2f}%)")

        if llm is not None and not llm.trade_allowed:
            reasons.append("LLM recommendation: trade not allowed")

        if llm is not None and llm.setup_quality < self.settings.min_model_confidence:
            reasons.append(f"LLM setup quality {llm.setup_quality:.2f} below threshold")

        # Asset-class specific placeholders
        if signal.asset_class == "CASH" and self.settings.max_forex_leverage < 1:
            reasons.append("Forex leverage check failed")

        approved = len(reasons) == 0
        qty = None
        if approved:
            qty = size_by_risk(
                equity,
                signal,
                self.settings.max_risk_per_trade_pct,
                self.settings.max_contracts_per_trade,
            )
            if qty <= 0:
                approved = False
                reasons.append("Position size computed as zero")

        if not approved:
            logger.warning("Risk check failed for {}: {}", signal.symbol, reasons)

        return RiskCheckResult(approved=approved, reasons=reasons, adjusted_quantity=qty)
