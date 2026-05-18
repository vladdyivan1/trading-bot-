from __future__ import annotations

from config.settings import Settings
from risk.kill_switch import KillSwitch
from risk.risk_manager import AccountSnapshot, RiskManager
from strategies.base_strategy import StrategySignal


def make_signal() -> StrategySignal:
    return StrategySignal(
        symbol="SPY",
        asset_class="STK",
        timeframe="5 mins",
        direction="long",
        entry_price=500.0,
        stop_loss=498.0,
        take_profit=504.0,
        confidence_score=0.8,
        reason="test",
        strategy_name="moving_average_crossover",
    )


def test_risk_manager_allows_safe_trade():
    settings = Settings()
    risk = RiskManager(settings=settings)
    account = AccountSnapshot(account_equity=100_000)
    decision = risk.evaluate(
        signal=make_signal(),
        account=account,
        model_confidence=0.8,
        backtest_sample_size=100,
        spread_pct=0.1,
    )
    assert decision.trade_allowed
    assert decision.approved_quantity > 0


def test_risk_manager_blocks_on_daily_loss_and_confidence():
    settings = Settings(max_daily_loss_pct=2.0)
    risk = RiskManager(settings=settings)
    account = AccountSnapshot(account_equity=100_000, daily_pnl_pct=-2.5)
    decision = risk.evaluate(
        signal=make_signal(),
        account=account,
        model_confidence=0.5,
        backtest_sample_size=40,
        spread_pct=0.5,
    )
    assert not decision.trade_allowed
    assert any("Max daily loss" in reason for reason in decision.reasons)
    assert any("Model confidence" in reason for reason in decision.reasons)


def test_risk_manager_respects_kill_switch():
    kill = KillSwitch(enabled=True, reason="manual")
    risk = RiskManager(kill_switch=kill)
    account = AccountSnapshot(account_equity=100_000)
    decision = risk.evaluate(
        signal=make_signal(),
        account=account,
        model_confidence=0.8,
        backtest_sample_size=100,
        spread_pct=0.1,
    )
    assert not decision.trade_allowed
    assert any("Kill switch" in reason for reason in decision.reasons)
