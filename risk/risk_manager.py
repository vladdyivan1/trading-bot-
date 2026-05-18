"""Hard-coded risk checks for all trade execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from config.settings import Settings, settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import fixed_fractional_size, notional_value
from strategies.base_strategy import TradeSignal


class RiskContext(BaseModel):
    """Runtime portfolio and market context required for risk validation."""

    account_equity: float = Field(gt=0)
    peak_equity: float | None = None
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    open_positions: int = 0
    trades_today: int = 0
    current_quantity: float = 0.0
    current_price: float | None = None
    spread_pct: float | None = None
    backtest_trades: int = 0
    forex_notional: float = 0.0
    futures_notional: float = 0.0
    options_premium_at_risk: float = 0.0
    news_lockout: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class RiskDecision:
    allowed: bool
    reasons: list[str]
    quantity: int = 0
    risk_amount: float = 0.0


class RiskManager:
    """Deterministic risk engine. This is the final gate before execution."""

    def __init__(self, cfg: Settings = settings, kill_switch: KillSwitch | None = None) -> None:
        self.settings = cfg
        self.kill_switch = kill_switch or KillSwitch()

    def validate_signal(self, signal: TradeSignal, context: RiskContext) -> RiskDecision:
        reasons: list[str] = []
        if self.kill_switch.is_enabled():
            reasons.append(f"Kill switch enabled: {self.kill_switch.reason() or 'no reason provided'}")
        if signal.direction not in {"long", "short"}:
            reasons.append("Signal direction is not actionable")
        if signal.stop_loss is None or signal.take_profit is None:
            reasons.append("Signal must include stop_loss and take_profit")
        if signal.reward_risk is None or signal.reward_risk < self.settings.min_reward_risk:
            reasons.append(f"Reward/risk below minimum {self.settings.min_reward_risk}")
        if signal.confidence_score < self.settings.min_model_confidence:
            reasons.append(f"Confidence below minimum {self.settings.min_model_confidence}")
        if context.daily_pnl <= -context.account_equity * self.settings.max_daily_loss_pct:
            reasons.append("Max daily loss exceeded")
        if context.weekly_pnl <= -context.account_equity * self.settings.max_weekly_loss_pct:
            reasons.append("Max weekly loss exceeded")
        peak = context.peak_equity or context.account_equity
        if peak > 0 and (peak - context.account_equity) / peak >= self.settings.max_account_drawdown_pct:
            reasons.append("Max account drawdown exceeded")
        if context.open_positions >= self.settings.max_open_positions:
            reasons.append("Max open positions reached")
        if context.trades_today >= self.settings.max_trades_per_day:
            reasons.append("Max trades per day reached")
        if context.backtest_trades < self.settings.min_backtest_trades:
            reasons.append("Backtest sample size below minimum")
        if context.spread_pct is not None and context.spread_pct > self.settings.max_allowed_spread_pct:
            reasons.append("Spread exceeds maximum allowed")
        if context.news_lockout:
            reasons.append("News/event lockout active")

        quantity = 0
        risk_amount = 0.0
        if signal.stop_loss is not None:
            quantity = fixed_fractional_size(
                account_equity=context.account_equity,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                risk_fraction=self.settings.max_risk_per_trade_pct,
                max_quantity=self.settings.max_contracts_per_trade,
            )
            risk_amount = quantity * abs(signal.entry_price - signal.stop_loss)
            if quantity <= 0:
                reasons.append("Position size is zero")
            if risk_amount > context.account_equity * self.settings.max_risk_per_trade_pct:
                reasons.append("Risk amount exceeds max risk per trade")

        self._asset_class_checks(signal, context, quantity, reasons)
        return RiskDecision(allowed=not reasons, reasons=reasons, quantity=quantity, risk_amount=risk_amount)

    def _asset_class_checks(
        self,
        signal: TradeSignal,
        context: RiskContext,
        quantity: int,
        reasons: list[str],
    ) -> None:
        asset_class = signal.asset_class.upper()
        if asset_class == "CASH":
            projected = context.forex_notional + notional_value(quantity, signal.entry_price)
            max_notional = context.account_equity * self.settings.max_forex_leverage
            if projected > max_notional:
                reasons.append("Max forex leverage exceeded")
        elif asset_class == "FUT":
            projected = context.futures_notional + notional_value(quantity, signal.entry_price)
            max_notional = context.account_equity * self.settings.max_futures_exposure_pct
            if projected > max_notional:
                reasons.append("Max futures exposure exceeded")
        elif asset_class == "OPT":
            premium_risk = context.options_premium_at_risk + notional_value(quantity, signal.entry_price, 100)
            max_premium = context.account_equity * self.settings.max_options_premium_risk_pct
            if premium_risk > max_premium:
                reasons.append("Max options premium risk exceeded")

    def live_trading_guard(self) -> None:
        if not self.settings.live_trading_allowed:
            raise PermissionError("Live trading is disabled by default")
