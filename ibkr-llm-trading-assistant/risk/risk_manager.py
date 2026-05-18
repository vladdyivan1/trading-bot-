"""Deterministic risk engine — blocks unsafe trades."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from config.settings import Settings, get_settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import calculate_position_size
from schemas import AssetClass, BacktestResult, RiskCheckResult, TradeSignal


class RiskManager:
    """Hard-coded risk checks — LLM cannot bypass."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.kill_switch = KillSwitch()
        self._daily_pnl: float = 0.0
        self._weekly_pnl: float = 0.0
        self._peak_equity: float = 0.0
        self._trades_today: int = 0
        self._last_reset: datetime = datetime.utcnow()
        self._news_lockout: bool = False

    def reset_daily_counters(self, account_value: float) -> None:
        now = datetime.utcnow()
        if now.date() != self._last_reset.date():
            self._daily_pnl = 0.0
            self._trades_today = 0
            self._last_reset = now
        if now - self._last_reset > timedelta(days=7):
            self._weekly_pnl = 0.0

    def validate_signal(
        self,
        signal: TradeSignal,
        account_value: float,
        open_positions: int,
        backtest_result: Optional[BacktestResult] = None,
        model_confidence: Optional[float] = None,
        spread_pct: float = 0.0,
    ) -> RiskCheckResult:
        """Run all risk checks on a trade signal."""
        reasons: list[str] = []

        if not self.kill_switch.check():
            return RiskCheckResult(approved=False, reasons=[f"Kill switch: {self.kill_switch.reason}"])

        if self.settings.live_trading_enabled and not self.settings.ibkr_paper:
            if not self.settings.live_trading_enabled:
                reasons.append("Live trading not explicitly enabled")

        if not self.settings.paper_trading_enabled and not self.settings.live_trading_enabled:
            reasons.append("All trading disabled in config")

        self.reset_daily_counters(account_value)

        if self._peak_equity == 0:
            self._peak_equity = account_value
        self._peak_equity = max(self._peak_equity, account_value)

        max_daily_loss = account_value * (self.settings.max_daily_loss_pct / 100)
        if self._daily_pnl <= -max_daily_loss:
            reasons.append(f"Max daily loss reached ({self.settings.max_daily_loss_pct}%)")

        max_weekly_loss = account_value * (self.settings.max_weekly_loss_pct / 100)
        if self._weekly_pnl <= -max_weekly_loss:
            reasons.append(f"Max weekly loss reached ({self.settings.max_weekly_loss_pct}%)")

        drawdown = (self._peak_equity - account_value) / self._peak_equity * 100
        if drawdown >= self.settings.max_account_drawdown_pct:
            reasons.append(f"Max account drawdown ({drawdown:.1f}%)")

        if open_positions >= self.settings.max_open_positions:
            reasons.append(f"Max open positions ({self.settings.max_open_positions})")

        if self._trades_today >= self.settings.max_trades_per_day:
            reasons.append(f"Max trades per day ({self.settings.max_trades_per_day})")

        if signal.reward_to_risk < self.settings.min_reward_to_risk:
            reasons.append(
                f"R:R {signal.reward_to_risk:.2f} below minimum {self.settings.min_reward_to_risk}"
            )

        confidence = model_confidence or signal.confidence_score
        if confidence < self.settings.min_model_confidence:
            reasons.append(
                f"Confidence {confidence:.2f} below minimum {self.settings.min_model_confidence}"
            )

        if backtest_result and backtest_result.num_trades < self.settings.min_backtest_trades:
            reasons.append(
                f"Backtest sample {backtest_result.num_trades} < {self.settings.min_backtest_trades}"
            )

        if spread_pct > self.settings.max_allowed_spread_pct:
            reasons.append(f"Spread {spread_pct:.2f}% exceeds max {self.settings.max_allowed_spread_pct}%")

        if self._news_lockout:
            reasons.append("News/event lockout active")

        if signal.asset_class == AssetClass.CASH:
            leverage = signal.quantity or 1
            if leverage > self.settings.max_forex_leverage:
                reasons.append("Max forex leverage exceeded")

        if reasons:
            logger.warning("Risk check FAILED for {}: {}", signal.symbol, reasons)
            return RiskCheckResult(approved=False, reasons=reasons)

        quantity = calculate_position_size(
            account_value,
            signal,
            self.settings.max_risk_per_trade_pct,
            self.settings.max_contracts_per_trade,
        )
        logger.info("Risk check PASSED for {} qty={}", signal.symbol, quantity)
        return RiskCheckResult(approved=True, reasons=[], adjusted_quantity=quantity)

    def record_trade_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl
        self._weekly_pnl += pnl
        self._trades_today += 1

    def set_news_lockout(self, active: bool) -> None:
        self._news_lockout = active
