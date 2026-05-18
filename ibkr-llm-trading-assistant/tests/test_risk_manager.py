"""Tests for risk manager and position sizing."""

import pytest

from config.settings import Settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import calculate_position_size
from risk.risk_manager import RiskManager
from schemas import AssetClass, BacktestResult, Direction, TradeSignal, Timeframe


@pytest.fixture
def risk_manager():
    settings = Settings(
        max_risk_per_trade_pct=0.5,
        max_daily_loss_pct=2.0,
        max_open_positions=3,
        min_reward_to_risk=1.5,
        min_model_confidence=0.65,
        min_backtest_trades=30,
        paper_trading_enabled=True,
        live_trading_enabled=False,
    )
    return RiskManager(settings)


@pytest.fixture
def valid_signal():
    return TradeSignal(
        symbol="SPY",
        asset_class=AssetClass.STK,
        timeframe=Timeframe.M5,
        direction=Direction.LONG,
        entry_price=500.0,
        stop_loss=497.5,
        take_profit=505.0,
        confidence_score=0.75,
        reason="test",
        strategy_name="test",
    )


def test_position_sizing(valid_signal):
    qty = calculate_position_size(100000, valid_signal, 0.5, 1000)
    assert qty >= 1
    assert qty <= 1000


def test_risk_approves_valid_trade(risk_manager, valid_signal):
    backtest = BacktestResult(
        strategy_name="test",
        symbol="SPY",
        timeframe="5 mins",
        total_return=10.0,
        cagr=5.0,
        win_rate=55.0,
        profit_factor=1.5,
        max_drawdown=5.0,
        avg_win=100,
        avg_loss=-50,
        expectancy=25,
        sharpe_ratio=1.2,
        sortino_ratio=1.0,
        num_trades=50,
        avg_hold_time_hours=2.0,
    )
    result = risk_manager.validate_signal(
        valid_signal, account_value=100000, open_positions=0, backtest_result=backtest
    )
    assert result.approved
    assert result.adjusted_quantity is not None


def test_risk_blocks_low_confidence(risk_manager, valid_signal):
    valid_signal.confidence_score = 0.3
    result = risk_manager.validate_signal(
        valid_signal, account_value=100000, open_positions=0
    )
    assert not result.approved
    assert any("Confidence" in r for r in result.reasons)


def test_risk_blocks_max_positions(risk_manager, valid_signal):
    result = risk_manager.validate_signal(
        valid_signal, account_value=100000, open_positions=5
    )
    assert not result.approved


def test_risk_blocks_poor_rr(risk_manager):
    signal = TradeSignal(
        symbol="SPY",
        asset_class=AssetClass.STK,
        timeframe=Timeframe.M5,
        direction=Direction.LONG,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit=100.5,
        confidence_score=0.8,
        reason="test",
    )
    result = risk_manager.validate_signal(signal, 100000, 0)
    assert not result.approved


def test_kill_switch_blocks(risk_manager, valid_signal):
    ks = KillSwitch()
    ks.deactivate()
    ks.activate("test")
    result = risk_manager.validate_signal(valid_signal, 100000, 0)
    assert not result.approved
    ks.deactivate()


def test_daily_loss_limit(risk_manager, valid_signal):
    risk_manager._daily_pnl = -3000
    result = risk_manager.validate_signal(valid_signal, 100000, 0)
    assert not result.approved
