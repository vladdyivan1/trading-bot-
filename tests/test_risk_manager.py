from dataclasses import replace

from config.settings import settings
from risk.kill_switch import KillSwitch
from risk.position_sizing import fixed_fractional_size
from risk.risk_manager import RiskContext, RiskManager
from strategies.base_strategy import TradeSignal


def _signal(confidence: float = 0.8) -> TradeSignal:
    return TradeSignal(
        symbol="SPY",
        asset_class="STK",
        timeframe="1 day",
        direction="long",
        entry_price=100,
        stop_loss=99,
        take_profit=102,
        confidence_score=confidence,
        reason="test",
    )


def test_position_sizing_uses_fixed_fractional_risk():
    assert fixed_fractional_size(100_000, 100, 99, 0.005, max_quantity=1000) == 500


def test_risk_manager_allows_safe_trade(tmp_path):
    cfg = replace(settings, min_backtest_trades=10)
    kill_switch = KillSwitch(tmp_path / "kill")
    manager = RiskManager(cfg, kill_switch)
    context = RiskContext(account_equity=100_000, peak_equity=100_000, backtest_trades=25)

    decision = manager.validate_signal(_signal(), context)

    assert decision.allowed
    assert decision.quantity == 500
    assert decision.reasons == []


def test_risk_manager_blocks_low_confidence_and_daily_loss(tmp_path):
    cfg = replace(settings, min_backtest_trades=10)
    manager = RiskManager(cfg, KillSwitch(tmp_path / "kill"))
    context = RiskContext(account_equity=100_000, daily_pnl=-2_000, backtest_trades=25)

    decision = manager.validate_signal(_signal(confidence=0.1), context)

    assert not decision.allowed
    assert "Confidence below minimum" in " ".join(decision.reasons)
    assert "Max daily loss exceeded" in decision.reasons
