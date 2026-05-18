"""Deterministic risk manager for trade validation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from config.settings import Settings, get_settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import calculate_position_size, reward_risk_ratio
from strategies.base_strategy import StrategySignal


class AccountSnapshot(BaseModel):
    account_equity: float = Field(gt=0)
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    open_positions: int = 0
    trades_today: int = 0


class RiskDecision(BaseModel):
    trade_allowed: bool
    reasons: list[str] = Field(default_factory=list)
    approved_quantity: int = 0


class RiskManager:
    """Hard-coded risk controls. LLM cannot bypass this class."""

    def __init__(self, settings: Settings | None = None, kill_switch: KillSwitch | None = None) -> None:
        self.settings = settings or get_settings()
        self.kill_switch = kill_switch or KillSwitch()

    def evaluate(
        self,
        signal: StrategySignal,
        account: AccountSnapshot,
        model_confidence: float,
        backtest_sample_size: int,
        spread_pct: float,
        forex_leverage: float = 1.0,
        futures_exposure_pct: float = 0.0,
        options_premium_risk_pct: float = 0.0,
        news_lockout: bool = False,
    ) -> RiskDecision:
        reasons: list[str] = []

        if self.kill_switch.enabled:
            reasons.append(f"Kill switch active: {self.kill_switch.reason}")

        if news_lockout:
            reasons.append("News/event lockout is active")

        if account.daily_pnl_pct <= -self.settings.max_daily_loss_pct:
            reasons.append("Max daily loss reached")

        if account.weekly_pnl_pct <= -self.settings.max_weekly_loss_pct:
            reasons.append("Max weekly loss reached")

        if account.drawdown_pct >= self.settings.max_account_drawdown_pct:
            reasons.append("Max account drawdown exceeded")

        if account.open_positions >= self.settings.max_open_positions:
            reasons.append("Max open positions reached")

        if account.trades_today >= self.settings.max_trades_per_day:
            reasons.append("Max trades per day reached")

        rr = reward_risk_ratio(signal.entry_price, signal.stop_loss, signal.take_profit)
        if rr < self.settings.min_reward_risk:
            reasons.append("Reward/risk ratio below minimum")

        if model_confidence < self.settings.min_model_confidence:
            reasons.append("Model confidence below minimum")

        if signal.confidence_score < self.settings.min_model_confidence:
            reasons.append("Signal confidence below minimum")

        if backtest_sample_size < self.settings.min_backtest_sample_size:
            reasons.append("Insufficient backtest sample size")

        if spread_pct > self.settings.max_allowed_spread_pct:
            reasons.append("Spread too wide")

        if signal.asset_class == "FX" and forex_leverage > self.settings.max_forex_leverage:
            reasons.append("Forex leverage exceeds maximum")

        if signal.asset_class == "FUT" and futures_exposure_pct > self.settings.max_futures_exposure_pct:
            reasons.append("Futures exposure exceeds maximum")

        if signal.asset_class == "OPT" and options_premium_risk_pct > self.settings.max_options_premium_risk_pct:
            reasons.append("Options premium risk exceeds maximum")

        quantity = calculate_position_size(
            account_equity=account.account_equity,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            max_risk_pct=self.settings.max_risk_per_trade_pct,
            max_units=self.settings.max_contracts_per_trade,
        )

        if quantity <= 0:
            reasons.append("Calculated quantity is zero")

        if quantity > self.settings.max_contracts_per_trade:
            reasons.append("Contracts exceed maximum per trade")

        return RiskDecision(
            trade_allowed=len(reasons) == 0,
            reasons=reasons,
            approved_quantity=quantity if not reasons else 0,
        )
